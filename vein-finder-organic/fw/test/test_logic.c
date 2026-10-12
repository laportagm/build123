/*
 * Host unit tests for fw/src/logic.c (gcc, no hardware):  make -C fw test
 * Personal prototype for bench evaluation - NOT a medical device.
 */
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "../src/logic.h"

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

/* every tick run through ticks() is watched: lit_ticks counts ticks with the driver or a
 * bank gate on, so a test can check that a whole sequence never lit the LEDs */
static unsigned long lit_ticks;
static void ticks(vf_state_t *s, unsigned n)
{
    while (n--) {
        logic_tick(s);
        if (s->ctrl_permille || s->gate_a || s->gate_b)
            lit_ticks++;
    }
}
static void press(vf_state_t *s, unsigned n_ticks) { s->btn_down = true; ticks(s, n_ticks); s->btn_down = false; ticks(s, 4); }
static void tap(vf_state_t *s) { press(s, 5); }                       /* 80 ms */
static void hold(vf_state_t *s) { press(s, HOLD_TICKS + 5); }

static void test_levels(void)
{
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    ticks(&s, 5);
    CHECK(!s.on && s.ctrl_permille == 0 && s.want_sleep, "starts off and sleepy");
    tap(&s);
    CHECK(s.on && s.level == 0 && s.gate_a && !s.gate_b, "tap -> on, level 1, bank A");
    CHECK(s.ctrl_permille == CAP_A_PERMILLE * 400 / 1000, "level 1 duty %u", s.ctrl_permille);
    tap(&s); CHECK(s.level == 1 && s.ctrl_permille == CAP_A_PERMILLE * 700 / 1000, "level 2 duty %u", s.ctrl_permille);
    tap(&s); CHECK(s.level == 2 && s.ctrl_permille == CAP_A_PERMILLE, "level 3 duty %u", s.ctrl_permille);
    tap(&s); CHECK(!s.on && s.ctrl_permille == 0 && !s.gate_a && !s.gate_b, "fourth tap -> off");
}

static void test_bank_switch(void)
{
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s); tap(&s); tap(&s);                         /* level 3, bank A */
    s.btn_down = true;
    unsigned saw_both = 0, n = 0;
    for (unsigned i = 0; i < HOLD_TICKS + 5; i++) {
        logic_tick(&s);
        if (s.gate_a && s.gate_b) saw_both++;
        n++;
    }
    s.btn_down = false; ticks(&s, 4);
    CHECK(s.on && s.bank == BANK_B && !s.gate_a && s.gate_b, "hold -> bank B");
    CHECK(saw_both == MBB_TICKS, "make-before-break overlap %u tick(s)", saw_both);
    CHECK(s.level == 2 && s.ctrl_permille == CAP_B_PERMILLE, "hold keeps the level; bank B cap %u", s.ctrl_permille);
    hold(&s);
    CHECK(s.bank == BANK_A && s.gate_a && !s.gate_b, "hold again -> bank A");
    logic_init(&s); s.t_dc = 300; s.vbat_mv = 3900;
    hold(&s);
    CHECK(!s.on, "hold while off does nothing");
}

static void test_auto_off(void)
{
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s);
    ticks(&s, AUTO_OFF_TICKS - 10);
    CHECK(s.on, "still on just before 3 min");
    ticks(&s, 20);
    CHECK(!s.on && s.ctrl_permille == 0, "off after 3 min idle");
    unsigned long ms = (unsigned long)AUTO_OFF_TICKS * TICK_US / 1000u;
    CHECK(ms >= 179000 && ms <= 181000, "auto-off %lu ms", ms);
    unsigned long hold_ms = (unsigned long)HOLD_TICKS * TICK_US / 1000u;
    CHECK(hold_ms >= 580 && hold_ms <= 620, "hold %lu ms", hold_ms);
}

static void test_vbus(void)
{
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s);
    s.vbus = true; s.charging = true; ticks(&s, 2);
    CHECK(!s.on && s.ctrl_permille == 0 && s.seam == SEAM_CHARGING, "USB present: LEDs off, seam charging");
    tap(&s);
    CHECK(!s.on, "tap ignored while charging");
    s.charging = false; ticks(&s, 2);
    CHECK(s.seam == SEAM_FULL && !s.want_sleep, "full: steady seam, stays awake on USB");
    s.vbus = false; ticks(&s, 2);
    CHECK(s.want_sleep, "unplugged: sleeps");
}

static void test_thermal(void)
{
    CHECK(derate_permille(INT16_MIN) == 1000, "no reading: no derate");
    CHECK(derate_permille(300) == 1000 && derate_permille(T_DERATE_DC) == 1000, "below 38 C: full");
    CHECK(derate_permille(390) == 600, "39 C: %u", derate_permille(390));
    CHECK(derate_permille(T_LIMIT_DC) == DERATE_FLOOR_PERMILLE, "40 C: floor");
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s); tap(&s); tap(&s);
    s.t_dc = 395; ticks(&s, 2);
    CHECK(s.ctrl_permille == CAP_A_PERMILLE * 400 / 1000, "39.5 C derates to 40 %%: %u", s.ctrl_permille);
    s.t_dc = T_CUTOFF_DC; ticks(&s, 2);
    CHECK(s.ctrl_permille == 0 && s.hot_lock && s.seam == SEAM_HOT, "41 C: LEDs off, seam warns");
    s.t_dc = 390; ticks(&s, 2);
    CHECK(s.ctrl_permille == 0, "stays off above 38 C (hysteresis)");
    s.t_dc = 375; ticks(&s, 2);
    CHECK(s.ctrl_permille == CAP_A_PERMILLE && !s.hot_lock, "back on below 38 C");
}

static void test_battery(void)
{
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s);
    s.vbat_mv = 3350; ticks(&s, 2);
    CHECK(s.on && s.seam == SEAM_LOW_BATT, "3.35 V: on, seam warns");
    s.vbat_mv = 3150; ticks(&s, 2);
    CHECK(!s.on && s.batt_lock, "3.15 V: off");
    tap(&s);
    CHECK(!s.on, "cannot turn on while locked");
    s.vbat_mv = 3550; ticks(&s, 2); tap(&s);
    CHECK(s.on, "unlocks at 3.55 V (rest or charge)");
}

static void test_ntc(void)
{
    /* compare with the Beta model of the table generator (fw/tools/ntc_table.py) */
    double worst = 0;
    for (int t10 = 50; t10 <= 650; t10 += 5) {
        double T = t10 / 10.0 + 273.15;
        double R = 10e3 * exp(3380.0 * (1.0 / T - 1.0 / 298.15));
        uint16_t adc = (uint16_t)lround(1023.0 * R / (R + 10e3));
        double err = fabs(ntc_adc_to_dc(adc) / 10.0 - t10 / 10.0);
        if (err > worst) worst = err;
    }
    CHECK(worst < 0.35, "NTC table error %.2f C", worst);
    printf("  NTC conversion: worst error %.2f C over 5-65 C\n", worst);
    /* open NTC (input at full scale): reported as a fault and locks the LEDs off */
    CHECK(ntc_adc_to_dc(1023) == T_SENSOR_FAULT_DC && ntc_adc_to_dc(NTC_ADC_OPEN) == T_SENSOR_FAULT_DC,
          "open NTC -> fault");
    CHECK(ntc_adc_to_dc(NTC_ADC_OPEN - 1) == 0, "cold but plausible -> 0 C");
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s);
    s.t_dc = ntc_adc_to_dc(1023); ticks(&s, 2);
    CHECK(s.ctrl_permille == 0 && s.hot_lock && s.seam == SEAM_HOT, "open NTC: LEDs off, seam warns");
}

/* ------------------------------------------------------------ safety (chunk 1) */

static void test_init_safe(void)
{
    vf_state_t s; logic_init(&s);
    CHECK(!s.on && s.ctrl_permille == 0 && !s.gate_a && !s.gate_b && s.t_dc == INT16_MIN && !s.want_sleep,
          "init: off, driver and gates off, no reading");
    lit_ticks = 0;
    ticks(&s, 100);                                    /* no inputs at all */
    CHECK(lit_ticks == 0 && !s.on, "idle with no inputs: never lit");
}

static void test_no_reading(void)
{
    /* N02: no light before the first temperature reading */
    vf_state_t s; logic_init(&s);
    s.vbat_mv = 3900;                                  /* t_dc left at INT16_MIN */
    lit_ticks = 0;
    tap(&s); tap(&s); tap(&s); hold(&s);
    CHECK(lit_ticks == 0, "taps and a hold before the first reading: never lit (%lu ticks)", lit_ticks);
    s.t_dc = 300; ticks(&s, 1);
    CHECK(s.on && s.ctrl_permille > 0, "lit on the first tick with a reading");
}

static void test_thermal_boundaries(void)
{
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s); tap(&s); tap(&s);                         /* level 3, bank A */
    s.t_dc = T_CUTOFF_DC - 1; ticks(&s, 1);            /* 40.9 C */
    CHECK(!s.hot_lock && s.gate_a && s.ctrl_permille == CAP_A_PERMILLE * DERATE_FLOOR_PERMILLE / 1000,
          "40.9 C: lit at the 20 %% floor (%u)", s.ctrl_permille);
    s.t_dc = T_CUTOFF_DC; ticks(&s, 1);                /* 41.0 C */
    CHECK(s.hot_lock && s.ctrl_permille == 0 && !s.gate_a && !s.gate_b, "41.0 C: off on the same tick");
    s.t_dc = T_DERATE_DC + 1; ticks(&s, 1);            /* 38.1 C */
    CHECK(s.hot_lock && s.ctrl_permille == 0, "38.1 C: still off");
    s.t_dc = T_DERATE_DC; ticks(&s, 1);                /* 38.0 C */
    CHECK(!s.hot_lock && s.ctrl_permille == CAP_A_PERMILLE, "38.0 C: back on at the level (%u)", s.ctrl_permille);
}

static void test_hot_lock_inputs(void)
{
    /* while locked hot, no tap, hold or replug may light the LEDs */
    vf_state_t s; logic_init(&s);
    s.t_dc = T_CUTOFF_DC; s.vbat_mv = 3900;
    ticks(&s, 2);
    lit_ticks = 0;
    for (int i = 0; i < 9; i++) tap(&s);               /* through every level, twice */
    tap(&s); hold(&s); hold(&s);                       /* bank switches */
    s.vbus = true; ticks(&s, 10); s.vbus = false; ticks(&s, 10);
    tap(&s);
    s.t_dc = T_DERATE_DC + 1; ticks(&s, 10);           /* cooling, but not enough */
    CHECK(lit_ticks == 0 && s.hot_lock, "hot lock holds against every input (%lu ticks lit)", lit_ticks);
}

static void test_ntc_faults(void)
{
    /* shorted NTC (or open R8 / NTC_EN stuck low): input near 0 V -> reads as 70 C -> off */
    CHECK(ntc_adc_to_dc(0) == 700 && ntc_adc_to_dc(188) == 700, "shorted NTC -> 70 C");
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s);
    s.t_dc = ntc_adc_to_dc(0); ticks(&s, 1);
    CHECK(s.ctrl_permille == 0 && !s.gate_a && !s.gate_b && s.hot_lock, "shorted NTC: off on the first reading");
    /* every reading from 0 to full scale converts to something that is either in the table's
     * range or the fault value, and is monotonic (higher count = colder) */
    int16_t prev = INT16_MAX - 1;
    bool mono = true, range = true;
    for (uint16_t a = 0; a < 1024; a++) {
        int16_t t = ntc_adc_to_dc(a);
        if (a >= NTC_ADC_OPEN) { range &= (t == T_SENSOR_FAULT_DC); continue; }
        range &= (t >= 0 && t <= 700);
        mono &= (t <= prev);
        prev = t;
    }
    CHECK(range && mono, "conversion over 0-1023: in range %d, monotonic %d", range, mono);
}

static void test_stuck_button(void)
{
    /* N01: a button held down (stuck, or pressed in a bag) must not defeat the auto-off */
    vf_state_t s; logic_init(&s);
    s.t_dc = 300; s.vbat_mv = 3900;
    tap(&s);                                           /* on, bank A */
    s.btn_down = true;                                 /* ...and now it sticks */
    ticks(&s, DEBOUNCE_TICKS + HOLD_TICKS);            /* the hold fires once: bank B */
    CHECK(s.on && s.bank == BANK_B, "stuck: one hold");
    ticks(&s, AUTO_OFF_TICKS - 2);
    CHECK(s.on, "stuck: still on just before 3 min after the hold");
    ticks(&s, 4);
    CHECK(!s.on && s.ctrl_permille == 0 && !s.gate_a && !s.gate_b, "stuck: off 3 min after the hold");
    lit_ticks = 0;
    ticks(&s, 10 * AUTO_OFF_TICKS);
    CHECK(lit_ticks == 0 && !s.on, "stuck: stays off");
    s.btn_down = false; ticks(&s, 4);                  /* released at last: it was a hold, not a tap */
    CHECK(!s.on && s.want_sleep, "release after a stuck press: still off, may sleep");
}

/* Random inputs, checked against the safety rules after every tick.  The rules are written
 * from the specification (logic.h), not from logic.c.  Deterministic (xorshift32). */
static uint32_t rng;
static uint32_t rnd(void) { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; }
static uint32_t rnd_in(uint32_t lo, uint32_t hi) { return lo + rnd() % (hi - lo + 1u); }

static uint32_t ref_derate(int16_t t)      /* the derating curve as specified */
{
    if (t <= T_DERATE_DC) return 1000u;
    if (t >= T_LIMIT_DC) return DERATE_FLOOR_PERMILLE;
    return 1000u - (uint32_t)(t - T_DERATE_DC) * (1000u - DERATE_FLOOR_PERMILLE) / (T_LIMIT_DC - T_DERATE_DC);
}

static void random_run(uint32_t seed, uint32_t n)
{
    rng = seed;
    vf_state_t s; logic_init(&s);
    bool hot = false, low = false;                     /* reference latches */
    uint32_t btn_left = 1, vbus_left = 1, since_edge = 0, both_run = 0;
    unsigned long bad[9] = {0}, lit = 0, hot_on = 0, low_on = 0, mbb = 0, stuck = 0, vbus_ticks = 0;
    const uint32_t use_window = AUTO_OFF_TICKS + DEBOUNCE_TICKS + HOLD_TICKS;
    s.t_dc = INT16_MIN; s.vbat_mv = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (--btn_left == 0) {                         /* button: bounce, taps, holds, stuck */
            s.btn_down = !s.btn_down;
            since_edge = 0;
            uint32_t r = rnd() % 1000u;
            btn_left = r < 300 ? rnd_in(1, 3) : r < 900 ? rnd_in(3, 80) : r < 995 ? rnd_in(80, 4000)
                                                           : rnd_in(AUTO_OFF_TICKS, 3u * AUTO_OFF_TICKS);
            if (btn_left > AUTO_OFF_TICKS && s.btn_down) stuck++;
        } else {
            since_edge++;
        }
        if (--vbus_left == 0) {                        /* USB: mostly absent */
            s.vbus = !s.vbus && (rnd() % 4u == 0);
            vbus_left = s.vbus ? rnd_in(10, 20000) : rnd_in(10, 60000);
        }
        s.charging = s.vbus && (rnd() % 2u);
        if (i % 16u == 0) {                            /* readings every 250 ms, as main.c */
            uint32_t r = rnd() % 10000u;
            if (r < 2) s.t_dc = T_SENSOR_FAULT_DC;     /* open NTC */
            else if (r < 4) s.t_dc = 700;              /* shorted NTC */
            else if (r < 5) s.t_dc = INT16_MIN;        /* no reading */
            else {
                int32_t t = (s.t_dc < 250 || s.t_dc > 470) ? 360 : s.t_dc;
                t += (int32_t)rnd_in(0, 8) - 4;
                s.t_dc = (int16_t)(t < 300 ? 300 : t > 450 ? 450 : t);
            }
            r = rnd() % 10000u;
            if (r < 3) s.vbat_mv = 0;                  /* not measured */
            else {
                int32_t v = s.vbat_mv ? s.vbat_mv : 3700;
                v += (int32_t)rnd_in(0, 40) - 20;
                s.vbat_mv = (uint16_t)(v < 3000 ? 3000 : v > 4200 ? 4200 : v);
            }
        }
        logic_tick(&s);

        if (s.t_dc != INT16_MIN) {                     /* reference latches, from the spec */
            if (s.t_dc >= T_CUTOFF_DC) hot = true;
            else if (s.t_dc <= T_DERATE_DC) hot = false;
        }
        if (s.vbat_mv) {
            if (s.vbat_mv < VBAT_CUTOFF_MV) low = true;
            else if (s.vbat_mv >= VBAT_RESUME_MV) low = false;
        }
        bool any = s.ctrl_permille || s.gate_a || s.gate_b;
        uint32_t cap = s.bank == BANK_A ? CAP_A_PERMILLE : CAP_B_PERMILLE;
        both_run = (s.gate_a && s.gate_b) ? both_run + 1 : 0;
        /* 0: no light when hot, low, on USB, with no reading, or off */
        if (any && (hot || low || s.vbus || s.t_dc == INT16_MIN || !s.on)) bad[0]++;
        /* 1: never above the bank's cap, or above the derated cap */
        if (s.ctrl_permille > cap || s.ctrl_permille > cap * ref_derate(s.t_dc) / 1000u) bad[1]++;
        /* 2: the driver never runs without a string to drive (open-LED overvoltage) */
        if (s.ctrl_permille && !s.gate_a && !s.gate_b) bad[2]++;
        /* 3: a bank gate is never on without the driver */
        if ((s.gate_a || s.gate_b) && !s.ctrl_permille) bad[3]++;
        /* 4: both strings together for at most the make-before-break overlap */
        if (both_run > MBB_TICKS) bad[4]++;
        /* 5: never lit 3 min after the last button edge that could be a tap or a hold */
        if (any && since_edge >= use_window) bad[5]++;
        /* 6: only sleep when off, dark, button up and no USB */
        if (s.want_sleep && (s.on || any || s.btn_down || s.vbus)) bad[6]++;
        /* 7: outside the overlap, the lit gate is the selected bank's */
        if (s.ctrl_permille && both_run == 0 && s.gate_a != (s.bank == BANK_A)) bad[7]++;
        /* 8: the level is always one of the three */
        if (s.level > 2) bad[8]++;

        lit += s.ctrl_permille != 0;
        hot_on += s.on && hot;
        low_on += low;
        mbb += both_run == 1;
        vbus_ticks += s.vbus;
    }
    static const char *const RULE[9] = {
        "lit while hot/low/USB/no reading/off", "duty above the (derated) cap", "driver on with no string",
        "gate on with the driver off", "overlap longer than make-before-break", "lit 3 min after the last use",
        "sleep while lit or busy", "wrong bank lit", "level out of range"};
    for (int k = 0; k < 9; k++)
        CHECK(bad[k] == 0, "seed %u: rule %d (%s) broken on %lu ticks", (unsigned)seed, k, RULE[k], bad[k]);
    /* the run must have exercised what it checks */
    CHECK(lit > n / 50 && hot_on > 1000 && low_on > 1000 && mbb > 20 && stuck > 3 && vbus_ticks > 10000,
          "seed %u: coverage lit %lu, hot-while-on %lu, low %lu, bank switches %lu, stuck %lu, usb %lu",
          (unsigned)seed, lit, hot_on, low_on, mbb, stuck, vbus_ticks);
    printf("  random seed %u: %u ticks (%.1f h); lit %lu, hot-while-on %lu, low %lu, switches %lu, stuck %lu\n",
           (unsigned)seed, (unsigned)n, n * (TICK_US / 1e6) / 3600.0, lit, hot_on, low_on, mbb, stuck);
}

static void test_random_invariants(void)
{
    random_run(0x2545F491u, 4000000u);
    random_run(0x9E3779B9u, 4000000u);
    random_run(12345u, 4000000u);
}

int main(void)
{
    test_levels(); test_bank_switch(); test_auto_off(); test_vbus(); test_thermal(); test_battery(); test_ntc();
    test_init_safe(); test_no_reading(); test_thermal_boundaries(); test_hot_lock_inputs(); test_ntc_faults();
    test_stuck_button(); test_random_invariants();
    if (fails) { printf("%d failure(s)\n", fails); return 1; }
    printf("all logic tests passed\n");
    return 0;
}
