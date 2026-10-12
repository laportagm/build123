/*
 * Vein finder (organic) - device logic, free of hardware access so it can be unit-tested
 * on the host (fw/test/test_logic.c).  main.c feeds it the button level, the sensor
 * readings and a 15.6 ms tick, and applies the outputs it returns.
 *
 * Personal prototype for bench evaluation - NOT a medical device.
 */
#ifndef VF_LOGIC_H
#define VF_LOGIC_H

#include <stdbool.h>
#include <stdint.h>

/* ------------------------------------------------------------------ configuration */
#define TICK_US              15625u       /* RTC PIT period: 16 cycles of the 1.024 kHz clock */
#define DEBOUNCE_TICKS       2u           /* 2 consecutive equal samples */
#define HOLD_TICKS           (600000UL / TICK_US)        /* 0.6 s press = hold (38 ticks) */
#define AUTO_OFF_TICKS       (180000000UL / TICK_US)     /* 3 min without a press (11520 ticks) */
#define MBB_TICKS            1u           /* make-before-break overlap when switching banks */

/* LED current caps per bank, as a fraction of the hardware ceiling (VREF / R_SET =
 * 204 mV / 8.2 ohm = 24.9 mA): bank A 660 nm 23 mA (thermal study), bank B 625 nm 24.9 mA */
#define CAP_A_PERMILLE       925u
#define CAP_B_PERMILLE       1000u

/* temperature limits at the NTC (0.7 mm under the skin-contact face), in 0.1 C */
#define T_DERATE_DC          380          /* start reducing current */
#define T_LIMIT_DC           400          /* current at the floor (20 %) */
#define T_CUTOFF_DC          410          /* LEDs off until the face cools below T_DERATE */
#define DERATE_FLOOR_PERMILLE 200u

/* battery (cell voltage under load, mV) */
#define VBAT_LOW_MV          3400u        /* warn: seam blinks */
#define VBAT_CUTOFF_MV       3200u        /* LEDs off */
#define VBAT_RESUME_MV       3500u        /* allow again after a rest / charge */

typedef enum { BANK_A = 0, BANK_B = 1 } bank_t;

typedef enum {
    SEAM_OFF = 0, SEAM_ON, SEAM_CHARGING, SEAM_FULL, SEAM_LOW_BATT, SEAM_HOT, SEAM_BANK_FLASH
} seam_mode_t;

typedef struct {
    /* inputs, set by main.c before logic_tick() */
    bool btn_down;            /* debounced in logic (raw level here) */
    bool vbus;                /* USB power present */
    bool charging;            /* charger /CHG low */
    int16_t t_dc;             /* NTC temperature, 0.1 C; INT16_MIN = not measured */
    uint16_t vbat_mv;         /* 0 = not measured */

    /* state */
    bool on;
    bank_t bank;
    uint8_t level;            /* 0..2 */
    uint8_t btn_stable, btn_count;
    uint16_t press_ticks;
    bool hold_done;
    uint32_t idle_ticks;
    bool hot_lock, batt_lock;
    uint8_t flash_ticks;
    uint8_t mbb_ticks;
    bank_t prev_bank;
    uint16_t anim;

    /* outputs */
    uint16_t ctrl_permille;   /* CTRL PWM duty, 0 = driver off */
    bool gate_a, gate_b;
    uint16_t seam_permille;
    seam_mode_t seam;
    bool want_sleep;          /* nothing to do: main.c may power down */
} vf_state_t;

void logic_init(vf_state_t *s);
void logic_tick(vf_state_t *s);
uint16_t derate_permille(int16_t t_dc);

/* NTC: 10 k / 10 k divider, NTC to GND, ratiometric 10-bit reading -> 0.1 C.  An open NTC
 * (or a broken NTC_SENSE joint) pulls the input to full scale; a reading at or above
 * NTC_ADC_OPEN (about -50 C on the Beta model) is a sensor fault and is reported as
 * T_SENSOR_FAULT_DC, which the logic treats as over-temperature (LEDs off). */
#define NTC_ADC_OPEN         1000u
#define T_SENSOR_FAULT_DC    INT16_MAX
int16_t ntc_adc_to_dc(uint16_t adc);

#endif
