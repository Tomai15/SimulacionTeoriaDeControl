import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


class SondaLambdaSimulator:
    def __init__(self):
        # --- Parámetros de Simulación ---
        self.scan_time_ms = 20  # Tiempo de scan de la ECU (20 ms)
        self.scan_time_s = self.scan_time_ms / 1000.0
        self.current_time = 0

        # --- Parámetros de Control (Controlador PI) ---
        self.setpoint_v = 0.45  # Setpoint (0.45V) - Punto estequiométrico (λ=1)
        self.Kp = 3.0  # Ganancia Proporcional (ajustada para respuesta rápida)
        self.Ki = 6.0  # Ganancia Integral (alta para forzar oscilación controlada)
        self.integral_term = 0.0
        self.integral_max = 2.5  # Límite Anti-Windup

        # --- Parámetros del Actuador (Inyector) ---
        self.base_pulse_width_ms = 4.0  # Pulso base (ms) en ralentí
        self.min_pulse_width_ms = 1.5  # Límite mínimo de inyección
        self.max_pulse_width_ms = 8.0  # Límite máximo de inyección
        self.pulse_width_ms = self.base_pulse_width_ms
        # K_injector ajustado para que el sistema inicie cerca del equilibrio
        # Con 10 g/s de aire, necesitamos 10/14.7 = 0.68 g/s de combustible para λ=1
        # Con pulso base de 4ms: K = 0.68/4 = 0.17 g/s por ms
        self.K_injector = 0.165  # Ganancia (g/s por ms de pulso)

        # --- Parámetros de la Planta (Motor) ---
        self.caudal_aire_base_gs = 10.0  # Caudal de aire base (gramos/segundo)
        self.stoich_ratio = 14.7  # Relación Estequiométrica (14.7 g aire / 1 g comb.)
        self.rpm = 800  # RPM del motor (ralentí)
        self.temperatura_ambiente_c = 20.0  # Temperatura ambiente (°C)
        self.presion_atmosferica_hpa = 1013.0  # Presión atmosférica (hPa) - nivel del mar

        # --- Parámetros de Perturbación (Editables desde GUI) ---
        self.perturbacion_amplitud = 0.0  # Amplitud de la perturbación (g/s de aire)
        self.perturbacion_inicio = 5.0  # Tiempo de inicio de la perturbación (s)
        self.perturbacion_duracion = 5.0  # Duración de la perturbación (s)
        self.pert_comb_calidad = 1.0  # 1.0 = ideal, 0.9 = 10% peor (fijo)
        self.pert_ruido_emi_v = 0.015  # Ruido de +/- 15mV (20-30mV p-p según TP)

        # --- Parámetros del Sensor (Sonda Lambda Bosch LSH-25) ---
        # Constantes de tiempo asimétricas del sensor (según TP)
        self.tau_rica_pobre_s = 0.050  # 50ms (Rica -> Pobre, 0.8V -> 0.2V)
        self.tau_pobre_rica_s = 0.080  # 80ms (Pobre -> Rica, 0.2V -> 0.8V)

        # --- Variables de Estado y Retardo ---
        # Voltaje ideal instantáneo (sin retardo del sensor)
        self.voltaje_sonda_ideal = 0.45
        # Voltaje con dinámica del sensor (filtrado)
        self.voltaje_sonda_filtrado = 0.45
        # Voltaje de realimentación (con ruido)
        self.voltaje_sonda_realimentacion = 0.45
        # Estado anterior para detectar transiciones
        self.voltaje_anterior = 0.45

        # --- Historial para Gráficos ---
        self.time_history = []
        self.setpoint_history = []  # Historial del setpoint (entrada de referencia)
        self.voltaje_sonda_history = []  # Voltaje del elemento de medición
        self.pulse_width_history = []  # Salida del controlador
        self.caudal_aire_history = []  # Perturbación
        self.lambda_history = []  # Salida del sistema
        self.o2_percent_history = []  # %O2 en gases de escape (salida del motor)
        self.error_history = []  # Error
        self.accion_p_history = []
        self.accion_i_history = []
        self.perturbacion_aplicada_history = []  # Perturbación aplicada en cada instante

    def step(self):
        """ Ejecuta un ciclo de control (scan) """

        # 1. CÁLCULO DEL CONTROLADOR (PI) - Implementado en la ECU
        # El error se calcula con la medición del ciclo ANTERIOR (modelando el retardo digital)
        error = self.setpoint_v - self.voltaje_sonda_realimentacion

        # Acción Proporcional
        accion_p = self.Kp * error

        # Acción Integral (con anti-windup)
        self.integral_term += error * self.scan_time_s
        self.integral_term = max(-self.integral_max, min(self.integral_term, self.integral_max))
        accion_i = self.Ki * self.integral_term

        # Corrección total (en ms)
        correccion_pi_ms = accion_p + accion_i

        # Señal de control final (saturada) - DAC/PWM convierte a pulso temporal
        self.pulse_width_ms = self.base_pulse_width_ms + correccion_pi_ms
        self.pulse_width_ms = max(self.min_pulse_width_ms, min(self.pulse_width_ms, self.max_pulse_width_ms))

        # 2. SIMULAR PERTURBACIONES
        # Perturbación de Caudal de Aire (Externa)
        # Condiciones fijas: temperatura 20°C, presión nivel del mar, ralentí
        caudal_aire_base_gs = self.caudal_aire_base_gs

        # Aplicar perturbación tipo escalón si estamos en el rango de tiempo especificado
        perturbacion_actual = 0.0
        if self.perturbacion_inicio <= self.current_time < (self.perturbacion_inicio + self.perturbacion_duracion):
            perturbacion_actual = self.perturbacion_amplitud

        # Ruido aleatorio pequeño (simulando variaciones naturales del motor)
        ruido_aire = np.random.uniform(-0.05, 0.05)

        caudal_aire_actual_gs = caudal_aire_base_gs + perturbacion_actual + ruido_aire

        # Perturbación de Calidad de Combustible (Interna)
        # Se aplica como un factor de eficiencia al flujo de combustible
        flujo_combustible_efectivo_gs = (self.pulse_width_ms * self.K_injector) * self.pert_comb_calidad

        # 3. SIMULAR PLANTA (PROCESO DE COMBUSTIÓN EN EL MOTOR)
        # Calcular Lambda (λ = relación aire/combustible real / relación estequiométrica)
        if flujo_combustible_efectivo_gs > 0:
            lambda_real = (caudal_aire_actual_gs / flujo_combustible_efectivo_gs) / self.stoich_ratio
        else:
            lambda_real = 5.0  # Mezcla infinitamente pobre

        # Calcular %O2 en los gases de escape (salida del motor)
        # Aproximación: relación entre lambda y %O2 en el escape
        # λ < 1 (rica): ~0.1-0.5% O2
        # λ = 1 (estequiométrica): ~0.5% O2
        # λ > 1 (pobre): 0.5-4% O2
        if lambda_real < 1.0:
            # Mezcla rica: poco oxígeno residual
            o2_percent = 0.1 + 0.4 * lambda_real
        else:
            # Mezcla pobre: oxígeno residual aumenta linealmente
            o2_percent = 0.5 + 3.5 * (lambda_real - 1.0)
            o2_percent = min(o2_percent, 4.0)  # Limitar a 4%

        # 4. SIMULAR SENSOR (SONDA LAMBDA BOSCH LSH-25)
        # 4a. Característica no lineal del sensor (curva sigmoide)
        # Usamos tanh() para simular la curva "S" con salto brusco en λ=1
        # Si λ < 1 (rica, poco O2) → voltaje ALTO (>0.45V)
        # Si λ > 1 (pobre, mucho O2) → voltaje BAJO (<0.45V)
        self.voltaje_sonda_ideal = self.setpoint_v + 0.45 * np.tanh(20.0 * (1.0 - lambda_real))

        # 4b. Aplicar dinámica del sensor (constante de tiempo asimétrica)
        # Determinar la constante de tiempo según la dirección del cambio
        diferencia = self.voltaje_sonda_ideal - self.voltaje_sonda_filtrado

        if diferencia > 0:  # Pobre -> Rica (voltaje subiendo)
            tau_actual = self.tau_pobre_rica_s  # 80ms (más lento)
        else:  # Rica -> Pobre (voltaje bajando)
            tau_actual = self.tau_rica_pobre_s  # 50ms (más rápido)

        # Filtro de primer orden: dy/dt = (entrada - salida) / tau
        # Discretización: y[k] = y[k-1] + (Ts/tau) * (entrada - y[k-1])
        alpha = self.scan_time_s / tau_actual
        self.voltaje_sonda_filtrado += alpha * diferencia

        # 4c. Perturbación de Ruido EMI (Interferencia electromagnética del sistema de ignición)
        ruido_emi = np.random.uniform(-self.pert_ruido_emi_v, self.pert_ruido_emi_v)
        voltaje_sonda_medido = self.voltaje_sonda_filtrado + ruido_emi

        # 5. ADC - Conversión Analógico-Digital
        # El voltaje medido por el ADC es la realimentación para el próximo ciclo
        self.voltaje_sonda_realimentacion = voltaje_sonda_medido

        # 6. REGISTRAR HISTORIAL
        self.current_time += self.scan_time_s
        self.time_history.append(self.current_time)
        self.setpoint_history.append(self.setpoint_v)  # Entrada de referencia
        self.voltaje_sonda_history.append(self.voltaje_sonda_realimentacion)  # Elemento de medición
        self.pulse_width_history.append(self.pulse_width_ms)  # Salida del controlador
        self.caudal_aire_history.append(caudal_aire_actual_gs)  # Caudal total
        self.lambda_history.append(lambda_real)  # Salida del sistema
        self.o2_percent_history.append(o2_percent)  # %O2 en gases de escape
        self.error_history.append(error)  # Error
        self.accion_p_history.append(accion_p)
        self.accion_i_history.append(accion_i)
        self.perturbacion_aplicada_history.append(perturbacion_actual)  # Perturbación pura

        # Guardar estado anterior
        self.voltaje_anterior = self.voltaje_sonda_filtrado

        # 7. LOG (Opcional)
        if hasattr(self, "logger"):
            estado = "RICA" if self.voltaje_sonda_realimentacion > self.setpoint_v else "POBRE"
            pert_msg = f"Pert: {perturbacion_actual:.2f}g/s" if perturbacion_actual != 0 else "Sin Pert."
            log_msg = (f"T: {self.current_time:.2f}s | {pert_msg} | "
                       f"Estado: {estado} | "
                       f"V_sonda: {self.voltaje_sonda_realimentacion:.3f}V | "
                       f"Lambda: {lambda_real:.3f} | "
                       f"Error: {error:.3f}V | "
                       f"Pulso: {self.pulse_width_ms:.2f}ms")
            self.logger(log_msg)


class SondaLambdaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TP Teoría de Control - Sistema de Inyección Electrónica con Sonda Lambda")
        self.sim = SondaLambdaSimulator()
        self.sim.logger = self.log
        self.paused = False  # Estado de pausa

        label_font = ("Arial", 11)
        entry_font = ("Arial", 11)
        button_font = ("Arial", 12, "bold")

        # === PANEL DE CONTROL ===
        control_frame = tk.LabelFrame(root, text="Configuración de Perturbación y Controlador", font=("Arial", 12, "bold"), pady=15, padx=15)
        control_frame.pack(pady=10, padx=10, fill=tk.X)

        # Fila única con los parámetros de perturbación
        tk.Label(control_frame, text="Amplitud (g/s):", font=label_font).grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.amplitud_entry = tk.Entry(control_frame, font=entry_font, width=10)
        self.amplitud_entry.grid(row=0, column=1, padx=10, pady=5)
        self.amplitud_entry.insert(0, "0.0")

        tk.Label(control_frame, text="Tiempo de Inicio (s):", font=label_font).grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        self.inicio_entry = tk.Entry(control_frame, font=entry_font, width=10)
        self.inicio_entry.grid(row=0, column=3, padx=10, pady=5)
        self.inicio_entry.insert(0, "5.0")

        tk.Label(control_frame, text="Duración (s):", font=label_font).grid(row=0, column=4, sticky=tk.W, padx=10, pady=5)
        self.duracion_entry = tk.Entry(control_frame, font=entry_font, width=10)
        self.duracion_entry.grid(row=0, column=5, padx=10, pady=5)
        self.duracion_entry.insert(0, "5.0")

        # Parámetros del Controlador PI (a la derecha)
        tk.Label(control_frame, text="Kp:", font=label_font).grid(row=0, column=6, sticky=tk.W, padx=10, pady=5)
        self.kp_entry = tk.Entry(control_frame, font=entry_font, width=10)
        self.kp_entry.grid(row=0, column=7, padx=10, pady=5)
        self.kp_entry.insert(0, "3.0")

        tk.Label(control_frame, text="Ki:", font=label_font).grid(row=0, column=8, sticky=tk.W, padx=10, pady=5)
        self.ki_entry = tk.Entry(control_frame, font=entry_font, width=10)
        self.ki_entry.grid(row=0, column=9, padx=10, pady=5)
        self.ki_entry.insert(0, "6.0")

        tk.Label(control_frame, text="Setpoint (V):", font=label_font).grid(row=0, column=10, sticky=tk.W, padx=10, pady=5)
        self.setpoint_entry = tk.Entry(control_frame, font=entry_font, width=10)
        self.setpoint_entry.grid(row=0, column=11, padx=10, pady=5)
        self.setpoint_entry.insert(0, "0.45")

        # Botones de control
        apply_button = tk.Button(control_frame, text="Aplicar Perturbación", command=self.apply_parameters,
                                font=button_font, bg="#4CAF50", fg="white", padx=25)
        apply_button.grid(row=1, column=0, columnspan=3, pady=15, padx=5)

        self.pause_button = tk.Button(control_frame, text="⏸ Pausar Simulación", command=self.toggle_pause,
                                     font=button_font, bg="#2196F3", fg="white", padx=25)
        self.pause_button.grid(row=1, column=3, columnspan=3, pady=15, padx=5)

        apply_controller_button = tk.Button(control_frame, text="Aplicar Controlador", command=self.apply_controller_parameters,
                                           font=button_font, bg="#9C27B0", fg="white", padx=25)
        apply_controller_button.grid(row=1, column=6, columnspan=6, pady=15, padx=5)

        # === INDICADOR DE ESTADO ===
        self.estado_frame = tk.Frame(root, bg="#333333", pady=5)
        self.estado_frame.pack(pady=5, fill=tk.X)

        self.estado_label = tk.Label(self.estado_frame, text="ESTADO: INICIALIZANDO",
                                     font=("Arial", 13, "bold"), bg="#333333", fg="white")
        self.estado_label.pack()

        # Área de log
        log_frame = tk.LabelFrame(root, text="Log del Sistema", font=("Arial", 10, "bold"))
        log_frame.pack(pady=5, padx=10, fill=tk.BOTH)

        self.log_text = tk.Text(log_frame, height=6, width=120, font=("Courier New", 9))
        self.log_text.pack(pady=5, padx=5, fill=tk.BOTH)
        self.log_text.configure(state='disabled')

        # Gráfico en vivo
        self.fig, self.axes = plt.subplots(7, 1, figsize=(14, 12), sharex=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=self.sim.scan_time_ms)

    def apply_parameters(self):
        try:
            self.sim.perturbacion_amplitud = float(self.amplitud_entry.get())
            self.sim.perturbacion_inicio = float(self.inicio_entry.get())
            self.sim.perturbacion_duracion = float(self.duracion_entry.get())
            self.log(f">>> Perturbación configurada: Amplitud={self.sim.perturbacion_amplitud}g/s, "
                    f"Inicio={self.sim.perturbacion_inicio}s, Duración={self.sim.perturbacion_duracion}s <<<")
        except ValueError:
            self.log("ERROR: Parámetros inválidos. Verifique los valores ingresados.")

    def apply_controller_parameters(self):
        try:
            new_kp = float(self.kp_entry.get())
            new_ki = float(self.ki_entry.get())
            new_setpoint = float(self.setpoint_entry.get())

            # Validar rangos razonables
            if new_kp < 0 or new_ki < 0:
                self.log("ERROR: Kp y Ki deben ser valores positivos.")
                return
            if new_setpoint < 0.0 or new_setpoint > 1.0:
                self.log("ERROR: El setpoint debe estar entre 0.0V y 1.0V.")
                return

            # Aplicar cambios
            self.sim.Kp = new_kp
            self.sim.Ki = new_ki
            self.sim.setpoint_v = new_setpoint

            self.log(f">>> Parámetros del Controlador actualizados: Kp={new_kp}, Ki={new_ki}, Setpoint={new_setpoint}V <<<")
        except ValueError:
            self.log("ERROR: Parámetros del controlador inválidos. Verifique los valores ingresados.")

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_button.config(text="▶ Reanudar Simulación", bg="#FF9800")
            self.log(">>> Simulación PAUSADA <<<")
        else:
            self.pause_button.config(text="⏸ Pausar Simulación", bg="#2196F3")
            self.log(">>> Simulación REANUDADA <<<")

    def log(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def update_plot(self, i):
        # Solo avanzar la simulación si no está pausada
        if not self.paused:
            self.sim.step()

        # Actualizar indicador de estado
        if len(self.sim.voltaje_sonda_history) > 0:
            voltaje_actual = self.sim.voltaje_sonda_history[-1]
            if abs(voltaje_actual - self.sim.setpoint_v) < 0.05:
                estado = "ESTEQUIOMÉTRICO (λ≈1)"
                color = "#4CAF50"  # Verde
            elif voltaje_actual > self.sim.setpoint_v:
                estado = "MEZCLA RICA (Exceso Combustible)"
                color = "#FF9800"  # Naranja
            else:
                estado = "MEZCLA POBRE (Exceso Aire)"
                color = "#2196F3"  # Azul

            self.estado_label.config(text=f"ESTADO: {estado}", bg=color)
            self.estado_frame.config(bg=color)

        # Limitar el historial a los últimos 750 puntos (15 segundos)
        max_points = 750
        x = self.sim.time_history[-max_points:]
        setpoint = self.sim.setpoint_history[-max_points:]
        lambda_hist = self.sim.lambda_history[-max_points:]
        o2_percent = self.sim.o2_percent_history[-max_points:]
        error = self.sim.error_history[-max_points:]
        voltaje_medicion = self.sim.voltaje_sonda_history[-max_points:]
        pulso = self.sim.pulse_width_history[-max_points:]
        perturbacion = self.sim.perturbacion_aplicada_history[-max_points:]

        for ax in self.axes:
            ax.clear()
            ax.grid(True, alpha=0.3)

        # Gráfico 1: Voltaje de Entrada (Setpoint/Referencia)
        self.axes[0].plot(x, setpoint, label="r(t) - Setpoint (Entrada de Referencia)", color="red",
                         linewidth=2, linestyle="--")
        self.axes[0].set_ylabel("Voltaje (V)", fontweight='bold')
        self.axes[0].set_ylim(0.0, 1.0)
        self.axes[0].legend(loc='upper right', fontsize=9)
        self.axes[0].set_title("Sistema de Control de Inyección Electrónica - TP Teoría de Control",
                              fontweight='bold', fontsize=11)

        # Gráfico 2: Salida del Sistema (Lambda - Proceso de Combustión)
        self.axes[1].plot(x, lambda_hist, label="y(t) - Lambda (λ) - Salida del Sistema G(s)",
                         color="purple", linewidth=1.8)
        self.axes[1].axhline(1.0, label="λ=1 (Estequiométrico)", color="black", linestyle="--", linewidth=1.5)
        self.axes[1].fill_between(x, 0.98, 1.02, color='green', alpha=0.15, label='Banda óptima')
        self.axes[1].set_ylabel("Lambda (λ)", fontweight='bold')
        self.axes[1].set_ylim(0.85, 1.15)
        self.axes[1].legend(loc='upper right', fontsize=9)

        # Gráfico 3: Error (Setpoint - Realimentación)
        self.axes[2].plot(x, error, label="e(t) - Error del Sistema", color="darkred", linewidth=1.5)
        self.axes[2].axhline(0, color="gray", linestyle=":", linewidth=1.5)
        self.axes[2].set_ylabel("Error (V)", fontweight='bold')
        self.axes[2].legend(loc='upper right', fontsize=9)

        # Gráfico 4: Voltaje del Elemento de Medición (Sonda Lambda)
        self.axes[3].plot(x, voltaje_medicion, label="f(t) - Voltaje Sonda Lambda H(s) (Realimentación)",
                         color="blue", linewidth=1.5)
        self.axes[3].axhline(self.sim.setpoint_v, label=f"Setpoint ({self.sim.setpoint_v}V)",
                            color="red", linestyle="--", linewidth=1.5)
        self.axes[3].fill_between(x, self.sim.setpoint_v - 0.015, self.sim.setpoint_v + 0.015,
                                 color='red', alpha=0.1, label='Exactitud (±15mV)')
        self.axes[3].set_ylabel("Voltaje (V)", fontweight='bold')
        self.axes[3].set_ylim(0.0, 1.0)
        self.axes[3].legend(loc='upper right', fontsize=9)

        # Gráfico 5: Salida del Controlador (Ancho de Pulso)
        self.axes[4].plot(x, pulso, label="u(t) - Ancho de Pulso (Salida Controlador PI)",
                         color="green", linewidth=1.5)
        self.axes[4].axhline(self.sim.base_pulse_width_ms, label=f"Pulso Base ({self.sim.base_pulse_width_ms}ms)",
                            color="gray", linestyle=":", linewidth=1.5)
        self.axes[4].set_ylabel("Pulso (ms)", fontweight='bold')
        self.axes[4].legend(loc='upper right', fontsize=9)

        # Gráfico 6: Perturbación (Caudal de Aire Extra)
        self.axes[5].plot(x, perturbacion, label="d(t) - Perturbación (Escalón de Aire)",
                         color="orange", linewidth=2, drawstyle='steps-post')
        self.axes[5].axhline(0, color="gray", linestyle=":", linewidth=1)
        self.axes[5].set_ylabel("Pert. (g/s)", fontweight='bold')
        self.axes[5].legend(loc='upper right', fontsize=9)

        # Gráfico 7: %O2 en Gases de Escape (Salida del Motor)
        self.axes[6].plot(x, o2_percent, label="%O2 - Salida del Motor (Gases de Escape)",
                         color="brown", linewidth=1.8)
        self.axes[6].axhline(0.5, label="%O2 Estequiométrico (~0.5%)",
                            color="black", linestyle="--", linewidth=1.5)
        self.axes[6].fill_between(x, 0.4, 0.6, color='green', alpha=0.15, label='Banda óptima')
        self.axes[6].set_ylabel("%O2", fontweight='bold')
        self.axes[6].set_xlabel("Tiempo (s)", fontweight='bold', fontsize=11)
        self.axes[6].set_ylim(0.3, 0.8)
        self.axes[6].legend(loc='upper right', fontsize=9)

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = SondaLambdaGUI(root)
    root.mainloop()