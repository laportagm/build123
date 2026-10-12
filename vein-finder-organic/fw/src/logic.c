/*
 * Vein finder (organic) - device logic (see logic.h).
 *
 *   tap  (< 0.6 s)   off -> level 1 (40 %) -> level 2 (70 %) -> level 3 (100 %) -> off
 *   hold (>= 0.6 s)  switch bank (660 nm <-> 625 nm), make-before-break, seam flashes twice
 *   3 min after the last tap or hold: off (a button held down does not count).
 *   USB power present: LEDs off, seam shows the charge.
 *   NTC above 38 C: current falls linearly to 20 % at 40 C; at 41 C the LEDs go off until
 *   the NTC is back at 38 C (an open or shorted NTC counts as too hot; no light before
 *   the first reading).  Cell under 3.4 V: seam warns; under 3.2 V: LEDs off.
 *
 * Personal prototype for bench evaluation - NOT a medical device.
 */
#include "logic.h"

#include <limits.h>

static const uint16_t LEVEL_PERMILLE[3] = {400u, 700u, 1000u};

void logic_init(vf_state_t *s)
{
    *s = (vf_state_t){0};
    s->t_dc = INT16_MIN;
    s->bank = BANK_A;
    s->prev_bank = BANK_A;
}

uint16_t derate_permille(int16_t t_dc)
{
    if (t_dc == INT16_MIN || t_dc <= T_DERATE_DC)
        return 1000u;
    if (t_dc >= T_LIMIT_DC)
        return DERATE_FLOOR_PERMILLE;
    /* linear from 1000 at T_DERATE to the floor at T_LIMIT */
    uint32_t span = (uint32_t)(T_LIMIT_DC - T_DERATE_DC);
    uint32_t over = (uint32_t)(t_dc - T_DERATE_DC);
    return (uint16_t)(1000u - (over * (1000u - DERATE_FLOOR_PERMILLE)) / span);
}

/* Beta model of the Murata NCP18XH103F03RB (B25/50 = 3380 K) on a 10 k / 10 k divider,
 * NTC to GND: ratio = R / (R + 10k).  Table every 5 C from 0 to 70 C (adc counts, 10 bit,
 * full scale 1023), linear interpolation in between. */
static const uint16_t NTC_TABLE[15] = {    /* computed by fw/tools/ntc_table.py */
    /* 0 C .. 70 C */ 755, 709, 661, 611, 561, 512, 464, 418, 376, 337, 301, 268, 238, 212, 189
};

int16_t ntc_adc_to_dc(uint16_t adc)
{
    if (adc >= NTC_ADC_OPEN)                /* open sensor: fail safe, as if too hot */
        return T_SENSOR_FAULT_DC;
    if (adc >= NTC_TABLE[0])
        return 0;
    for (uint8_t i = 1; i < 15; i++) {
        if (adc >= NTC_TABLE[i]) {
            uint16_t hi = NTC_TABLE[i - 1], lo = NTC_TABLE[i];
            /* temperature falls as the count falls: interpolate 50 (0.1 C) per step */
            return (int16_t)((i - 1) * 50 + ((uint32_t)(hi - adc) * 50u) / (hi - lo));
        }
    }
    return 700;
}

static void button(vf_state_t *s, bool *tap, bool *hold)
{
    *tap = *hold = false;
    /* debounce: the level must repeat DEBOUNCE_TICKS times */
    if (s->btn_down == (bool)s->btn_stable) {
        s->btn_count = 0;
    } else if (++s->btn_count >= DEBOUNCE_TICKS) {
        s->btn_stable = s->btn_down;
        s->btn_count = 0;
        if (s->btn_stable) {               /* press */
            s->press_ticks = 0;
            s->hold_done = false;
        } else if (!s->hold_done) {         /* release before the hold time: a tap */
            *tap = true;
        }
    }
    if (s->btn_stable) {
        if (s->press_ticks < UINT16_MAX)
            s->press_ticks++;
        if (!s->hold_done && s->press_ticks >= HOLD_TICKS) {
            s->hold_done = true;
            *hold = true;
        }
    }
}

void logic_tick(vf_state_t *s)
{
    bool tap, hold;
    button(s, &tap, &hold);
    s->anim++;

    /* only a tap or a hold counts as use: a button stuck down (in a bag) must not keep
     * the light on past the auto-off */
    if (tap || hold)
        s->idle_ticks = 0;
    else if (s->idle_ticks < UINT32_MAX)
        s->idle_ticks++;

    /* thermal latch with hysteresis */
    if (s->t_dc != INT16_MIN) {
        if (s->t_dc >= T_CUTOFF_DC)
            s->hot_lock = true;
        else if (s->t_dc <= T_DERATE_DC)
            s->hot_lock = false;
    }
    /* battery latch with hysteresis (vbat is measured under load while on) */
    if (s->vbat_mv) {
        if (s->vbat_mv < VBAT_CUTOFF_MV)
            s->batt_lock = true;
        else if (s->vbat_mv >= VBAT_RESUME_MV)
            s->batt_lock = false;
    }

    if (s->vbus) {
        s->on = false;                     /* no light while the cell charges */
    } else if (tap) {
        if (!s->on) {
            s->on = true;
            s->level = 0;
        } else if (s->level < 2) {
            s->level++;
        } else {
            s->on = false;
        }
    } else if (hold && s->on) {
        s->prev_bank = s->bank;
        s->bank = (s->bank == BANK_A) ? BANK_B : BANK_A;
        s->mbb_ticks = MBB_TICKS;
        s->flash_ticks = 24;               /* two flashes of the seam, ~0.4 s */
    }
    if (s->on && s->idle_ticks >= AUTO_OFF_TICKS)
        s->on = false;
    if (s->on && s->batt_lock)
        s->on = false;

    /* LED driver: never without a temperature reading */
    if (s->on && !s->hot_lock && s->t_dc != INT16_MIN) {
        uint32_t cap = (s->bank == BANK_A) ? CAP_A_PERMILLE : CAP_B_PERMILLE;
        uint32_t d = cap * LEVEL_PERMILLE[s->level] / 1000u;
        d = d * derate_permille(s->t_dc) / 1000u;
        s->ctrl_permille = (uint16_t)d;
        bool a = (s->bank == BANK_A), b = !a;
        if (s->mbb_ticks) {                /* both strings on for one tick */
            a = b = true;
            s->mbb_ticks--;
        }
        s->gate_a = a;
        s->gate_b = b;
    } else {
        s->ctrl_permille = 0;              /* CTRL low > 2.5 ms shuts the TPS61169 down */
        s->gate_a = s->gate_b = false;
        s->mbb_ticks = 0;
    }

    /* status seam */
    if (s->flash_ticks) {
        s->flash_ticks--;
        s->seam = SEAM_BANK_FLASH;
        s->seam_permille = ((s->flash_ticks / 6u) % 2u) ? 600u : 0u;
    } else if (s->vbus) {
        if (s->charging) {
            s->seam = SEAM_CHARGING;       /* slow breathing, ~3 s */
            uint16_t ph = s->anim % 192u;
            uint16_t tri = ph < 96u ? ph : 191u - ph;
            s->seam_permille = (uint16_t)(20u + tri * 3u);
        } else {
            s->seam = SEAM_FULL;
            s->seam_permille = 150u;
        }
    } else if (s->on && s->hot_lock) {
        s->seam = SEAM_HOT;                /* double blink every 2 s */
        uint16_t ph = s->anim % 125u;
        s->seam_permille = (ph < 6u || (ph >= 12u && ph < 18u)) ? 500u : 0u;
    } else if (s->on && s->vbat_mv && s->vbat_mv < VBAT_LOW_MV) {
        s->seam = SEAM_LOW_BATT;           /* 1 Hz blink */
        s->seam_permille = (s->anim % 62u) < 31u ? 300u : 0u;
    } else if (s->on) {
        s->seam = SEAM_ON;
        s->seam_permille = 40u;            /* a faint line: on, and which way the window faces */
    } else {
        s->seam = SEAM_OFF;
        s->seam_permille = 0;
    }
    s->want_sleep = !s->on && !s->vbus && !s->btn_stable && !s->btn_down && !s->flash_ticks;
}
