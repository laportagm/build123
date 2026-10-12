/*
 * Vein finder (organic) - ATtiny1614 firmware, hardware layer.
 *
 * Pins (ee/design.py, MCU_PINS):
 *   PA0 UPDI          PA1 NTC_SENSE (AIN1)   PA2 NTC_EN       PA3 GATE_A (660 nm)
 *   PA4 GATE_B (625)  PA5 /CHG (pull-up)     PA6 BTN (pull-up, fully async)
 *   PA7 VBUS_SENSE    PB0 LED_CTRL (TCA0 WO0, 20 kHz)        PB1 SEAM (TCA0 WO1)
 *   PB2 TX / PB3 RX   debug UART (VF_DEBUG builds only)
 *
 * The TPS61169 turns CTRL's PWM duty into its feedback reference (analog dimming, no
 * flicker); CTRL low for > 2.5 ms shuts it down (< 2 uA).  The LED current can never
 * exceed VREF / R9 (24.9 mA typ) whatever this code does.
 *
 * Personal prototype for bench evaluation - NOT a medical device.
 */
#ifndef F_CPU
#define F_CPU 3333333UL                 /* default: 20 MHz oscillator / 6 */
#endif

#include <avr/interrupt.h>
#include <avr/io.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay.h>

#include "logic.h"

#define PWM_HZ    20000UL
#define PWM_TOP   ((uint16_t)(F_CPU / PWM_HZ - 1))       /* 165 */

#define NTC_EN    PIN2_bm
#define GATE_A    PIN3_bm
#define GATE_B    PIN4_bm
#define CHG_N     PIN5_bm
#define BTN       PIN6_bm
#define VBUS      PIN7_bm

static volatile uint8_t g_tick;

ISR(RTC_PIT_vect)
{
    RTC.PITINTFLAGS = RTC_PI_bm;
    g_tick = 1;
}

ISR(PORTA_PORT_vect)
{
    PORTA.INTFLAGS = PORTA.INTFLAGS;      /* a wake-up source only */
}

/* ------------------------------------------------------------------ init */
static void io_init(void)
{
    PORTA.OUTCLR = NTC_EN | GATE_A | GATE_B;
    PORTA.DIRSET = NTC_EN | GATE_A | GATE_B;
    PORTA.PIN1CTRL = PORT_ISC_INPUT_DISABLE_gc;                    /* analog only */
    PORTA.PIN5CTRL = PORT_PULLUPEN_bm | PORT_ISC_BOTHEDGES_gc;    /* charger /CHG, open drain */
    PORTA.PIN6CTRL = PORT_PULLUPEN_bm | PORT_ISC_BOTHEDGES_gc;    /* button to GND */
    PORTA.PIN7CTRL = PORT_ISC_BOTHEDGES_gc;                        /* VBUS through 100k / 200k */
    PORTB.OUTCLR = PIN0_bm | PIN1_bm;
    PORTB.DIRSET = PIN0_bm | PIN1_bm;
    PORTB.PIN2CTRL = PORT_PULLUPEN_bm;                             /* debug pads idle high */
    PORTB.PIN3CTRL = PORT_PULLUPEN_bm;
}

static void pwm_init(void)
{
    TCA0.SINGLE.PER = PWM_TOP;
    TCA0.SINGLE.CMP0 = 0;
    TCA0.SINGLE.CMP1 = 0;
    TCA0.SINGLE.CTRLB = TCA_SINGLE_WGMODE_SINGLESLOPE_gc;         /* outputs enabled on demand */
    TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV1_gc | TCA_SINGLE_ENABLE_bm;
}

/* A compare value of 0 still gives a one-clock pulse each period (enough to keep the
 * TPS61169 alive at 0.6 %), so "off" disconnects the waveform and the port drives low. */
static void pwm_set(uint16_t ctrl_pm, uint16_t seam_pm)
{
    uint8_t en = TCA_SINGLE_WGMODE_SINGLESLOPE_gc;
    if (ctrl_pm) {
        TCA0.SINGLE.CMP0BUF = (uint16_t)(((uint32_t)ctrl_pm * (PWM_TOP + 1u)) / 1000u);
        en |= TCA_SINGLE_CMP0EN_bm;
    }
    if (seam_pm) {
        TCA0.SINGLE.CMP1BUF = (uint16_t)(((uint32_t)seam_pm * (PWM_TOP + 1u)) / 1000u);
        en |= TCA_SINGLE_CMP1EN_bm;
    }
    TCA0.SINGLE.CTRLB = en;
}

static void rtc_pit(uint8_t on)
{
    while (RTC.PITSTATUS)
        ;
    RTC.PITCTRLA = on ? (RTC_PERIOD_CYC16_gc | RTC_PITEN_bm) : 0;  /* 16 / 1.024 kHz = 15.6 ms */
}

static void rtc_init(void)
{
    while (RTC.STATUS)
        ;
    RTC.CLKSEL = RTC_CLKSEL_INT1K_gc;
    RTC.PITINTCTRL = RTC_PI_bm;
    rtc_pit(1);
}

/* WDT.CTRLA is synchronised to the WDT clock (2-3 cycles of 1.024 kHz): never write it
 * while an earlier write is still being synchronised (sleep and wake can be ms apart) */
static void wdt_on(void)
{
    while (WDT.STATUS & WDT_SYNCBUSY_bm)
        ;
    _PROTECTED_WRITE(WDT.CTRLA, WDT_PERIOD_1KCLK_gc);              /* ~1 s */
}

static void wdt_off(void)
{
    while (WDT.STATUS & WDT_SYNCBUSY_bm)
        ;
    _PROTECTED_WRITE(WDT.CTRLA, WDT_PERIOD_OFF_gc);
}

/* ------------------------------------------------------------------ ADC */
static uint16_t adc_read(uint8_t muxpos, uint8_t refsel)
{
    ADC0.CTRLA = ADC_ENABLE_bm;                                    /* 10 bit */
    ADC0.CTRLB = ADC_SAMPNUM_ACC8_gc;                              /* 8 samples, summed */
    ADC0.CTRLC = ADC_SAMPCAP_bm | refsel | ADC_PRESC_DIV4_gc;      /* 833 kHz */
    ADC0.CTRLD = ADC_INITDLY_DLY32_gc;
    ADC0.MUXPOS = muxpos;
    ADC0.INTFLAGS = ADC_RESRDY_bm;
    ADC0.COMMAND = ADC_STCONV_bm;
    while (!(ADC0.INTFLAGS & ADC_RESRDY_bm))
        ;
    uint16_t r = ADC0.RES >> 3;
    ADC0.CTRLA = 0;
    return r;
}

static int16_t read_ntc_dc(void)
{
    PORTA.OUTSET = NTC_EN;
    _delay_us(200);
    uint16_t a = adc_read(ADC_MUXPOS_AIN1_gc, ADC_REFSEL_VDDREF_gc);  /* ratiometric */
    PORTA.OUTCLR = NTC_EN;
    return ntc_adc_to_dc(a);
}

static uint16_t read_vdd_mv(void)
{
    VREF.CTRLA = VREF_ADC0REFSEL_1V1_gc;
    VREF.CTRLB = VREF_ADC0REFEN_bm;
    _delay_us(100);
    uint16_t a = adc_read(ADC_MUXPOS_INTREF_gc, ADC_REFSEL_VDDREF_gc);
    VREF.CTRLB = 0;
    return a ? (uint16_t)((1100UL * 1023UL) / a) : 0;
}

/* ------------------------------------------------------------------ outputs */
static void apply(const vf_state_t *s)
{
    if (s->gate_a)
        PORTA.OUTSET = GATE_A;
    if (s->gate_b)
        PORTA.OUTSET = GATE_B;
    pwm_set(s->ctrl_permille, s->seam_permille);
    if (!s->gate_a)                                                /* make before break */
        PORTA.OUTCLR = GATE_A;
    if (!s->gate_b)
        PORTA.OUTCLR = GATE_B;
}

static void deep_sleep(void)
{
    pwm_set(0, 0);
    PORTA.OUTCLR = GATE_A | GATE_B | NTC_EN;
    rtc_pit(0);
    wdt_off();
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);                           /* ~0.1 uA; pins wake it */
    /* A press or USB power that arrived after the last tick has already been taken by the
     * pin ISR, and its edge would no longer wake the part: sleep only if neither is there. */
    cli();
    uint8_t in = PORTA.IN;
    if ((in & BTN) && !(in & VBUS)) {
        sleep_enable();
        sei();                                                     /* SLEEP runs before any pending ISR */
        sleep_cpu();
        sleep_disable();
    } else {
        sei();
    }
    wdt_on();
    rtc_pit(1);
}

int main(void)
{
    io_init();
    pwm_init();
    rtc_init();
    wdt_on();
    vf_state_t s;
    logic_init(&s);
    uint8_t slow = 0;
    sei();
    for (;;) {
        if (g_tick) {
            g_tick = 0;
            wdt_reset();
            uint8_t in = PORTA.IN;
            s.btn_down = !(in & BTN);
            s.vbus = (in & VBUS) != 0;
            s.charging = !(in & CHG_N);
            if (++slow >= 16) {                                    /* every 250 ms, and on waking */
                slow = 0;
                s.t_dc = read_ntc_dc();
                s.vbat_mv = read_vdd_mv();                         /* under load while lit */
            }
            logic_tick(&s);
            apply(&s);
        }
        if (s.want_sleep) {
            deep_sleep();
            s.want_sleep = false;                                  /* stale: decide again on the next tick */
            slow = 15;                                             /* measure soon after waking */
        } else {
            set_sleep_mode(SLEEP_MODE_IDLE);                       /* TCA keeps running */
            sleep_mode();
        }
    }
}
