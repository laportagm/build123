# Physics notes — concept-gate budgets

> Personal prototype for bench evaluation. **Not a medical device.** These are
> engineering estimates to size the concept, not a safety case.

## Units policy
SI inside every function (m, W, K, s, A, V, sr). Inputs that are naturally in mm or mA
carry the unit in the name (`r_mm`, `i_mA`) and are converted exactly once at the
function boundary. Photometric quantities: lm, lx, cd/m² (= nit).

## Models and governing equations

### 1. LED output
Photon flux to radiant flux: `P = Φ_p · N_A · h c / λ` (Φ_p in mol/s).
Drive scaling at low current (AlGaInP, well below rating): `P_opt ∝ I` (linear),
`V_f(I) = V_0 + R_s I` fitted through the datasheet typical point. Linear scaling slightly
*under*-estimates light at low current (efficiency rises), so it is conservative for
brightness and neutral for heating per watt of light.

Luminous efficacy of a narrow-band LED: `K = 683 · ∫V(λ)S(λ)dλ / ∫S(λ)dλ` with a Gaussian
spectrum `S` (peak, FWHM from the datasheet) and the CIE 1924 photopic `V(λ)` table.

### 2. Light transport in skin: steady-state diffusion (Farrell, Patterson & Wilson 1992)
Spatially resolved diffuse reflectance (fraction of injected power per unit area) at
distance ρ from a pencil source on a semi-infinite turbid medium:

```
R(ρ) = a'/(4π) [ z0 (μeff + 1/r1) e^(−μeff r1) / r1²  +  (z0 + 2zb)(μeff + 1/r2) e^(−μeff r2) / r2² ]
μt' = μa + μs',  a' = μs'/μt',  z0 = 1/μt',  D = 1/(3μt'),  zb = 2AD,  μeff = √(3 μa μt')
r1 = √(z0² + ρ²),  r2 = √((z0 + 2zb)² + ρ²),  A = (1 + r_d)/(1 − r_d)  (Groenhuis r_d(n))
```
Analytical pin: `∫ R(ρ) 2πρ dρ = (a'/2) e^(−√(3(1−a'))) (1 + e^(−(4/3)A√(3(1−a'))))`.
Limit: a' → 1 (no absorption) ⇒ total diffuse reflectance → 1.

Epidermal melanin (thin absorbing layer, crossed twice by transilluminated light):
`μa,mel(λ) = 6.6·10¹¹ λ_nm^−3.33 cm⁻¹ × f_mel`, `T_epi = exp(−μa,mel d_epi)`.

Window exitance from N sources: `M(q) = Σ P_inj,i T_epi² R(|q − p_i|)`, luminance
`L_v = K M / π` (Lambertian exit). Ambient veil in the window:
`L_amb = E_amb ρ_skin f_shade / π`.

### 3. Skin heating under one LED (steady state)
Absorbed power `P_abs = P_inj (1 − R_d T_epi²)` deposited in ≈ a hemisphere of radius a
under the pocket, insulated surface ⇒ image method ⇒ a full sphere with 2P_abs in an
infinite medium. Centre rise of a uniformly heated sphere: `ΔT = q a²/(2k)` with
`q = 2P_abs / (4/3 π a³)`, i.e.

```
ΔT_self = 3 P_abs / (4 π k a)
```
Neighbours (same bank) add `ΔT_j = P_abs / (2π k d_ij) · e^(−d_ij / L_p)` with the
perfusion length `L_p = √(k / (ω_b ρ_b c_b))`. Perfusion is ignored in ΔT_self
(conservative: a ≪ L_p).

### 4. Electrical chain
Boost CC driver: `P_in = I (N V_f + V_fb) / η`; battery power `P_bat = P_in + P_q`.
Runtime `t = E_usable / P_bat` with `E_usable = C · V_nom · u` (u = usable fraction).
Invariant: `P_in − P_out − P_loss = 0` and every term ≥ 0.

### 5. Photobiological (IEC 62471, preliminary)
Lambertian source radiance `L = Φ / (π A_src)`. Retinal thermal `L_R = Σ L_λ R(λ)Δλ`
(R = 1.0 for 500–700 nm); blue light `L_B = Σ L_λ B(λ)Δλ` (B = 0.001 for 600–700 nm).
Exempt-group comparisons use the limits as recalled for the concept gate; the
verification gate re-derives them from the standard's tables with the measurement
field-of-view rules (all marked "to verify").

## Assumptions (nominal, with the range used for sensitivity)
| Quantity | Nominal | Range | Basis |
|---|---|---|---|
| tissue index n | 1.40 | — | typical soft tissue |
| μs′ (dermis/subcutis mix) | 2.0 mm⁻¹ | 1.2–3.0 | Jacques 2013 skin & fat fits, 620–660 nm |
| blood volume fraction | 2 % | 1–3 % | forearm dermis/subcutis |
| SO₂ (mixed) | 0.75 | — | arterio-venous mix |
| background μa | 0.015 mm⁻¹ | 0.010–0.030 | bloodless tissue, 620–660 nm |
| epidermis thickness | 0.08 mm | — | forearm |
| melanosome fraction | 2 % / 10 % / 30 % | — | Fitzpatrick I–II / III–IV / V–VI |
| skin conductivity k | 0.37 W/m·K | 0.37–0.45 | dermis |
| deposition radius a | 2.0 mm | 1.5–3.0 | pocket aperture + scatter spread |
| baseline skin temperature | 33.5 °C | 32–35 | forearm, room 22–25 °C |
| ambient illuminance | 500 lx | 300–1000 | exam room |
| window shading factor | 0.5 | 0.3–0.7 | sky fraction seen through the window |
| LED→skin coupling | 0.75 | 0.6–0.85 | short black pocket, LED 1–3 mm above skin |
| boost efficiency | 0.85 | 0.80–0.88 | TPS61169-class at 0.3–1 W |
