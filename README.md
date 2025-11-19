# Sistema de Control de Inyección Electrónica con Sonda Lambda

Simulador interactivo de un sistema de control de inyección electrónica de combustible con realimentación de sensor de oxígeno (sonda lambda). Proyecto educativo de Teoría de Control.

## Tabla de Contenidos
- [Inicio Rápido (Windows)](#inicio-rápido-windows)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Cómo Ejecutar el Programa](#cómo-ejecutar-el-programa)
- [Uso del Simulador](#uso-del-simulador)
- [Solución de Problemas](#solución-de-problemas)

## Descripción

Este proyecto simula el sistema de control de combustible de un motor de combustión interna, utilizando un controlador PI (Proporcional-Integral) y una sonda lambda (sensor de oxígeno) para mantener la relación estequiométrica aire-combustible.

El simulador incluye:
- Controlador PI con ganancias Kp=3.0 y Ki=6.0
- Modelo de sensor de oxígeno Bosch LSH-25 con constantes de tiempo asimétricas
- Simulación de perturbaciones (variaciones de flujo de aire, calidad de combustible)
- Ruido electromagnético (EMI) gaussiano
- Interfaz gráfica con 7 gráficos en tiempo real
- Sistema de logs de eventos



## Requisitos Previos

Antes de ejecutar el programa, necesitas tener instalado:

- **Python 3.8 o superior** (recomendado Python 3.13)
  - Descargar desde: https://www.python.org/downloads/
  - Durante la instalación, asegúrate de marcar la opción "Add Python to PATH"

## Instalación

### Paso 1: Descargar el Proyecto

Descarga el archivo ZIP y descomprímelo en una carpeta.

### Paso 2: Crear un Entorno Virtual (Recomendado)

Es recomendable usar un entorno virtual para mantener las dependencias organizadas.

#### Primero, crea el entorno virtual:

**En Windows (CMD, PowerShell o Git Bash):**
```cmd
python -m venv .venv
```

**En Linux/Mac:**
```bash
python3 -m venv .venv
```

#### Luego, activa el entorno virtual:

**En Windows - CMD (Símbolo del sistema):**
```cmd
.venv\Scripts\activate.bat
```

**En Windows - PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**Nota para PowerShell:** Si recibes un error sobre políticas de ejecución, ejecuta primero:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**En Windows - Git Bash:**
```bash
source .venv/Scripts/activate
```

**En Linux/Mac:**
```bash
source .venv/bin/activate
```

Verás que tu terminal ahora muestra `(.venv)` al inicio de la línea, indicando que el entorno está activo.

### Paso 3: Instalar Dependencias

Con el entorno virtual activado, ejecuta el siguiente comando para instalar todas las bibliotecas necesarias:

**En Windows (CMD, PowerShell o Git Bash) y Linux/Mac:**
```
pip install -r requirements.txt
```

**Nota sobre tkinter:**
- **Windows:** `tkinter` viene incluido con la instalación estándar de Python. Si recibes un error, reinstala Python asegurándote de marcar "tcl/tk and IDLE" durante la instalación.
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt-get install python3-tk
  ```
- **Linux (Fedora):**
  ```bash
  sudo dnf install python3-tkinter
  ```
- **Mac:** `tkinter` viene incluido con la instalación estándar de Python.

## Cómo Ejecutar el Programa

Una vez instaladas las dependencias y con el entorno virtual activado, ejecuta:

**En Windows (CMD, PowerShell o Git Bash) y Linux/Mac:**
```
python app.py
```

Se abrirá una ventana con la interfaz gráfica del simulador.

**Importante:** Cada vez que cierres la terminal y quieras ejecutar el programa nuevamente, deberás activar el entorno virtual antes de ejecutar `python app.py`.

## Uso del Simulador

### Interfaz Gráfica

La interfaz está dividida en tres secciones:

1. **Panel de Control (Configuración de Perturbaciones)**
   - **Amplitud:** Magnitud de la perturbación (0-50%)
   - **Tiempo de inicio:** Momento en que comienza la perturbación (en segundos)
   - **Duración:** Duración de la perturbación (en segundos)
   - **Botones:** Aplicar y Reiniciar simulación

2. **Panel de Estado**
   - Indicador visual del estado del sistema:
     - Verde: Mezcla estequiométrica (λ ≈ 1.0)
     - Naranja: Mezcla rica (λ < 1.0)
     - Azul: Mezcla pobre (λ > 1.0)

3. **Gráficos en Tiempo Real (7 gráficas)**
   - Referencia (Setpoint): 0.45V
   - Salida Lambda: Relación aire-combustible
   - Error de control
   - Tensión de la sonda: Voltaje del sensor de O₂
   - Salida del controlador: Ancho de pulso del inyector
   - Perturbación aplicada
   - %O₂ en gases de escape

### Sistema de Logs

El panel inferior muestra eventos importantes:
- Cambios en el ancho de pulso del inyector
- Valores medidos del sensor
- Detección de mezcla rica/pobre
- Aplicación de perturbaciones

## Parámetros del Sistema

- **Tiempo de escaneo:** 20 ms (frecuencia de control de ECU)
- **RPM del motor:** 800 rpm (ralentí)
- **Setpoint:** 0.45V (punto estequiométrico)
- **Flujo de aire base:** 10 g/s
- **Relación estequiométrica:** 14.7:1 (aire:combustible)
- **Límites de pulso:** 1.5 - 8.0 ms
- **Rango del sensor:** 0.1V (pobre) - 0.9V (rico)

## Características Técnicas

- Implementación de controlador PI con anti-windup
- Modelado de constantes de tiempo asimétricas del sensor (50ms rico→pobre, 80ms pobre→rico)
- Curva característica no lineal del sensor (sigmoide)
- Simulación de ruido gaussiano (±15mV EMI)
- Modelado de conversión ADC/DAC
- Actualización en tiempo real a 50 FPS

## Estructura del Código

```
tpTeioriaDeControl/
├── app.py                                    # Archivo principal (simulador + GUI)
├── requirements.txt                          # Dependencias del proyecto
├── Trabajo final Teoria de control...pdf    # Documentación técnica del proyecto
├── README.md                                 # Este archivo
└── .venv/                                    # Entorno virtual (si lo creaste)
```

## Solución de Problemas

### Error al activar el entorno virtual en PowerShell
Si recibes el error: `"no se puede cargar el archivo... porque la ejecución de scripts está deshabilitada"`:

**Solución:**
1. Abre PowerShell como Administrador
2. Ejecuta:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. Confirma con "S" (Sí)
4. Cierra PowerShell y vuelve a intentar activar el entorno virtual

### Error: "No module named 'tkinter'"
- **Windows:** Reinstala Python desde python.org asegurándote de marcar "tcl/tk and IDLE" durante la instalación
- **Linux:** Instala `python3-tk` con tu gestor de paquetes:
  - Ubuntu/Debian: `sudo apt-get install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`

### Error: "No module named 'numpy'" o "No module named 'matplotlib'"
Este error generalmente ocurre porque:
1. El entorno virtual no está activado (verifica que veas `(.venv)` en tu terminal)
2. Las dependencias no se instalaron correctamente

**Solución:**
- Activa el entorno virtual según tu terminal (ver Paso 2)
- Ejecuta: `pip install -r requirements.txt`
- Si persiste el error, intenta: `pip install --upgrade pip` y luego vuelve a instalar las dependencias

### Error: "python: command not found" (Windows)
**Solución:**
1. Reinstala Python desde https://www.python.org/downloads/
2. Durante la instalación, asegúrate de marcar "Add Python to PATH"
3. Reinicia tu terminal después de la instalación

### La ventana no se abre o se cierra inmediatamente
- Verifica que tienes Python 3.8 o superior:
  ```
  python --version
  ```
- Asegúrate de que el entorno virtual esté activado (debe aparecer `(.venv)` en la terminal)
- Revisa los logs de error en la consola para ver mensajes específicos

### Los gráficos no se actualizan
- Asegúrate de tener matplotlib instalado correctamente
- Prueba reinstalando:
  - Windows: `pip uninstall matplotlib` seguido de `pip install matplotlib`
  - Linux/Mac: `pip uninstall matplotlib && pip install matplotlib`

### No puedo ver el archivo app.py
- Asegúrate de estar en la carpeta correcta del proyecto
- En la terminal, ejecuta:
  - Windows CMD/PowerShell: `dir`
  - Git Bash/Linux/Mac: `ls`
- Deberías ver `app.py` en la lista de archivos

## Autores

- **Tomas Valentín Delgado Andrade** (2035510)
- **Maria Isabella Innocente** (2037350)

## Contexto Académico

**Materia:** Teoría de Control
**Profesor:** Omar Oscár Civale
**Institución:** Universidada Tecnologica Nacional Facultad Regional Buenos Aires
**Año:** 2025

## Documentación Adicional

Para más información sobre el diseño del sistema de control, análisis de estabilidad y detalles técnicos, consulta el documento PDF incluido: `Trabajo final Teoria de control tomas isa.pdf`

## Licencia

Proyecto educativo desarrollado para fines académicos.
