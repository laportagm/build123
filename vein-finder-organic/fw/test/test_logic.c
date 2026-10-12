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

static void ticks(vf_state_t *s, unsigned n) { while (n--) logic_tick(s); }
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
    unsigned ms = AUTO_OFF_TICKS * TICK_MS;
    CHECK(ms >= 179000 && ms <= 181000, "auto-off %u ms", ms);
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
}

int main(void)
{
    test_levels(); test_bank_switch(); test_auto_off(); test_vbus(); test_thermal(); test_battery(); test_ntc();
    if (fails) { printf("%d failure(s)\n", fails); return 1; }
    printf("all logic tests passed\n");
    return 0;
}
