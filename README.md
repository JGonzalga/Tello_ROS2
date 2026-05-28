# tello_ros2 — Control del DJI Tello con ROS2 Humble

Paquete ROS2 Humble que permite:
- **Controlar** el DJI Tello con el teclado
- **Publicar** el stream de la cámara como topic `/tello/image_raw`
- **Visualizar** el video en **rqt** o **rqt_image_view**

---

## Tabla de contenidos

1. [Requisitos previos](#1-requisitos-previos)
2. [Estructura del repositorio](#2-estructura-del-repositorio)
3. [Instalación de dependencias](#3-instalación-de-dependencias)
4. [Configurar el workspace de ROS2](#4-configurar-el-workspace-de-ros2)
5. [Compilar el paquete](#5-compilar-el-paquete)
6. [Conectarse al Tello](#6-conectarse-al-tello)
7. [Ejecutar el driver y el teleop](#7-ejecutar-el-driver-y-el-teleop)
8. [Ver la cámara en rqt](#8-ver-la-cámara-en-rqt)
9. [Topics disponibles](#9-topics-disponibles)
10. [Controles del teclado](#10-controles-del-teclado)
11. [Parámetros configurables](#11-parámetros-configurables)
12. [Solución de problemas](#12-solución-de-problemas)

---

## 1. Requisitos previos

| Requisito | Versión mínima |
|-----------|---------------|
| Ubuntu    | 22.04 LTS     |
| ROS2      | Humble Hawksbill |
| Python    | 3.10+         |
| WiFi      | Necesario para conectarse al Tello |

> Si aún no tienes ROS2 Humble instalado, sigue la
> [guía oficial](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html).

---

## 2. Estructura del repositorio

```
tello_ros2/
├── requirements.txt
└── tello_driver/
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/
    │   └── tello_driver
    ├── config/
    │   └── tello_params.yaml
    ├── launch/
    │   ├── tello_bringup.launch.py   ← driver + teleop (recomendado)
    │   └── tello_driver.launch.py    ← solo driver
    └── tello_driver/
        ├── __init__.py
        ├── tello_driver_node.py      ← conexión UDP + cámara
        └── tello_teleop_key.py       ← control por teclado
```

---

## 3. Instalación de dependencias

### 3.1 Dependencias del sistema (ROS2)

```bash
sudo apt update
sudo apt install -y \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-rqt \
    ros-humble-rqt-image-view \
    python3-pip \
    xterm
```

### 3.2 Dependencias de Python

```bash
pip install djitellopy opencv-python
# o usando el archivo del repo:
pip install -r requirements.txt
```

---

## 4. Configurar el workspace de ROS2

Si ya tienes un workspace puedes saltar al paso 5.

```bash
# Crear workspace
mkdir -p ~/tello_ws/src
cd ~/tello_ws/src

# Clonar el repositorio (o copiar la carpeta tello_driver aquí)
git clone https://github.com/JGonzalga/DJI_Tello_ROS2.git
# Mueve el paquete al src del workspace:
cp -r DJI_Tello_ROS2/tello_driver ~/tello_ws/src/
```

---

## 5. Compilar el paquete

```bash
cd ~/tello_ws

# Sourcing de ROS2 (añadir al ~/.bashrc para no repetirlo)
source /opt/ros/humble/setup.bash

# Compilar solo este paquete
colcon build --packages-select tello_driver --symlink-install

# Hacer source del overlay generado
source install/setup.bash
```

> **Tip**: Añade `source ~/tello_ws/install/setup.bash` al final de tu `~/.bashrc`
> para no tener que ejecutarlo en cada terminal nueva.

```bash
echo "source ~/tello_ws/install/setup.bash" >> ~/.bashrc
```

---

## 6. Conectarse al Tello

1. **Enciende el Tello** — el LED parpadeará en amarillo.
2. En tu PC, abre la configuración WiFi y conéctate a la red
   `TELLO-XXXXXX` que crea el drone.
3. Verifica la conexión:
   ```bash
   ping 192.168.10.1
   ```
   Deberías ver respuestas sin pérdida de paquetes.

> Mientras estés conectado al Tello **perderás acceso a Internet**
> porque el drone actúa como punto de acceso WiFi.

---

## 7. Ejecutar el driver y el teleop

### Opción A — Todo en un comando (recomendado)

```bash
ros2 launch tello_driver tello_bringup.launch.py
```

Esto abre **dos terminales**:
- Una con el driver (logs de conexión, batería, estado)
- Una con el teleop (interfaz de teclado)

### Opción B — Terminales separadas

**Terminal 1 — Driver:**
```bash
ros2 launch tello_driver tello_driver.launch.py
```

**Terminal 2 — Teleop:**
```bash
ros2 run tello_driver tello_teleop_key
```

### Pasar parámetros al lanzar

```bash
# Cambiar IP y velocidad
ros2 launch tello_driver tello_bringup.launch.py tello_ip:=192.168.10.1 speed:=0.8

# FPS más bajo para reducir carga de CPU
ros2 launch tello_driver tello_bringup.launch.py stream_fps:=15
```

---

## 8. Ver la cámara en rqt

### Opción A — rqt_image_view (más simple)

```bash
ros2 run rqt_image_view rqt_image_view
```

En el menú desplegable selecciona el topic `/tello/image_raw`.

### Opción B — rqt completo

```bash
rqt
```

Luego: **Plugins → Visualization → Image View**
y selecciona `/tello/image_raw`.

### Opción C — Ver con herramientas de línea de comandos

```bash
# Ver info del topic
ros2 topic info /tello/image_raw

# Ver frecuencia real de publicación
ros2 topic hz /tello/image_raw

# Guardar un frame como imagen (requiere image_transport)
ros2 run image_transport republish raw in:=/tello/image_raw out:=/tello/image_compressed
```

---

## 9. Topics disponibles

| Topic | Tipo | Descripción |
|-------|------|-------------|
| `/tello/image_raw` | `sensor_msgs/Image` | Stream de video (BGR8) |
| `/tello/camera_info` | `sensor_msgs/CameraInfo` | Metadatos de la cámara |
| `/tello/battery` | `std_msgs/Int32` | Nivel de batería (%) |
| `/tello/state` | `std_msgs/String` | Estado completo del drone |
| `/tello/cmd_vel` | `geometry_msgs/Twist` | **Entrada** de velocidades |
| `/tello/takeoff` | `std_msgs/Empty` | **Entrada** despegar |
| `/tello/land` | `std_msgs/Empty` | **Entrada** aterrizar |
| `/tello/emergency` | `std_msgs/Empty` | **Entrada** parada de emergencia |

### Publicar comandos manualmente desde terminal

```bash
# Despegar
ros2 topic pub --once /tello/takeoff std_msgs/Empty '{}'

# Mover hacia adelante (30% de velocidad)
ros2 topic pub --rate 10 /tello/cmd_vel geometry_msgs/Twist \
  '{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {z: 0.0}}'

# Aterrizar
ros2 topic pub --once /tello/land std_msgs/Empty '{}'

# Ver batería
ros2 topic echo /tello/battery
```

---

## 10. Controles del teclado

```
╔══════════════════════════════════════════╗
║       TELLO KEYBOARD TELEOPERATION       ║
╠══════════════════════════════════════════╣
║  W/S  ── Forward / Backward             ║
║  A/D  ── Strafe Left / Right            ║
║  Q/E  ── Yaw Left / Right               ║
║  R/F  ── Up / Down                      ║
║                                          ║
║  T    ── TAKEOFF                         ║
║  L    ── LAND                            ║
║  SPACE── EMERGENCY STOP                  ║
║  ESC  ── Quit                            ║
╚══════════════════════════════════════════╝
```

> El drone tiene un **watchdog de seguridad**: si no recibe comandos
> durante 0.5 segundos, detiene automáticamente los motores
> (pero **no** aterriza).

---

## 11. Parámetros configurables

Edita `config/tello_params.yaml` o pásalos como argumentos de launch:

| Parámetro | Nodo | Default | Descripción |
|-----------|------|---------|-------------|
| `tello_ip` | driver | `192.168.10.1` | IP del drone |
| `stream_fps` | driver | `30` | FPS del video |
| `frame_width` | driver | `960` | Ancho del frame (px) |
| `frame_height` | driver | `720` | Alto del frame (px) |
| `cmd_vel_timeout` | driver | `0.5` | Timeout de seguridad (s) |
| `speed` | teleop | `0.6` | Velocidad de teleop (0–1) |

---

## 12. Solución de problemas

### `ModuleNotFoundError: djitellopy`
```bash
pip install djitellopy
# Si usas el Python del sistema con ROS:
pip3 install djitellopy --break-system-packages
```

### No se conecta al drone
- Verifica que estás conectado a la WiFi `TELLO-XXXXXX`
- Haz `ping 192.168.10.1` — si no responde, reinicia el drone
- El Tello solo acepta **una conexión a la vez**

### Error `cv_bridge` no encontrado
```bash
sudo apt install ros-humble-cv-bridge
```

### El video no aparece en rqt
```bash
# Verifica que el topic se está publicando
ros2 topic hz /tello/image_raw
# Deberías ver ~30 Hz
```

### El teleop no responde al teclado
- Asegúrate de que la ventana del teleop tiene el **foco del teclado**
- Si usas SSH, el teleop necesita una terminal TTY real
- Prueba ejecutar `tello_teleop_key` directamente en el equipo local

### `xterm: command not found`
```bash
sudo apt install xterm
```

---

## Licencia

MIT — Libre para uso personal, académico y comercial.
