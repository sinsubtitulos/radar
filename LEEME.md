# Vigía de vacantes · Radar Progresso

Revisa automáticamente las páginas de vacantes de las organizaciones del Radar, compara con la revisión anterior y te dice **qué vacantes son nuevas**, cuáles coinciden con el perfil del cliente y cuáles se cerraron.

## Qué produce cada corrida

| Archivo (carpeta `salida/`) | Para qué sirve |
|---|---|
| `reporte.html` | El reporte para leer: vacantes nuevas agrupadas por organización, páginas que cambiaron y páginas para revisar a mano. |
| `vacantes_nuevas.csv` | Las nuevas de esta corrida, para abrir en Excel. |
| `historial_vacantes_nuevas.csv` | Todas las nuevas detectadas desde el inicio. |
| `vacantes_activas.csv` | Todo lo publicado hoy en las páginas leídas. |
| `radar_vacantes.json` | El archivo que carga el Radar en el botón **«Vacantes detectadas»**. |

La memoria del sistema queda en `datos/estado.json`. No lo borres: es lo que permite saber qué es nuevo.

> **La primera corrida no muestra vacantes nuevas.** Registra todo lo publicado como *línea base*. Desde la segunda corrida verás solo lo que aparezca después.

## Cómo funciona

1. Lee `organizaciones.json`: las 496 organizaciones del Radar con su página de vacantes.
2. Según el tipo de página usa el lector adecuado:
   - **Plataformas de empleo** (Workday, Greenhouse, Workable, BambooHR, Lever, SmartRecruiters, Recruitee, Personio, Breezy) y **ReliefWeb**: lee su listado estructurado, que es exacto.
   - **Páginas propias** (la mayoría): busca enlaces cuyo texto parezca un cargo o convocatoria (coordinador, oficial, consultoría, términos de referencia, vacante…) y descarta menús, noticias y redes sociales.
   - Además guarda una «huella» de cada página. Si la página cambió pero no publica cada vacante como enlace (por ejemplo, convocatorias en PDF o en texto), aparece en **«Páginas que cambiaron»**.
3. Compara con la corrida anterior. Lo que no estaba es **nuevo**; lo que ya no aparece queda **cerrado**.
4. **Filtra por ubicación:** solo reporta como nuevas las vacantes en **Colombia o remotas**. Lee el lugar que publica la plataforma, el título y el texto junto al enlace. Si no dice dónde es, la asume en Colombia solo cuando la organización es colombiana (Red AFE, sitios .co o páginas de vacantes de oficinas en Colombia). Las demás se descartan y se cuentan en el reporte. Se ajusta en `config.yaml`, sección `ubicacion`.
   - Reconoce Colombia, las 32 capitales de departamento y Bogotá, los departamentos y unos 80 municipios sin doble sentido. Armenia, Florencia y Pasto solo cuentan con su departamento al lado («Armenia, Quindío»), porque también son un país, una ciudad italiana y una palabra común.
   - **Segunda mirada:** si una vacante nueva no dice dónde es, el vigía abre su ficha y busca el campo «Ubicación / Location / Duty station / Lugar de trabajo». Si es Colombia o remoto, la incluye; si es otro lugar, la descarta. Se puede apagar con `abrir_fichas: false` en `config.yaml`.
   - Las organizaciones colombianas cuyo sitio no termina en .co llevan `"pais": "CO"` en `organizaciones.json` (por ejemplo Fondo Acción, Dejusticia, Profamilia, Ruta N). Agrega esa marca a cualquier otra que publique solo vacantes en Colombia.
5. Marca las nuevas que contienen las palabras del perfil (`config.yaml`) y oculta las que contienen palabras excluidas (por ejemplo, «pasantía»).

**No se rastrean:** LinkedIn, WhatsApp, Facebook e Instagram (exigen inicio de sesión y sus condiciones lo prohíben), ni las 82 organizaciones sin página de vacantes. Aparecen en el reporte como «para revisar manualmente».

**Buenas prácticas incluidas:** respeta el archivo `robots.txt` de cada sitio, espera 2 segundos entre visitas al mismo sitio, se identifica como robot y solo lee páginas públicas.

---

## Opción A · Que corra solo en internet (recomendada)

Corre en GitHub Actions, gratis, de lunes a viernes a las 6:17 a. m. de Bogotá. No necesitas dejar tu computador encendido.

1. Crea una cuenta en [github.com](https://github.com) si no tienes.
2. Crea un repositorio nuevo (botón **New**), por ejemplo `radar-vigia`. Puede ser **privado**.
3. En el repositorio, entra a **Add file → Upload files** y arrastra **todo el contenido** de esta carpeta, incluida la carpeta `.github`.
   - Si tu sistema oculta la carpeta `.github`, créala desde GitHub: **Add file → Create new file**, escribe `.github/workflows/vigia.yml` como nombre y pega el contenido de ese archivo.
4. Ve a **Settings → Actions → General → Workflow permissions**, elige **Read and write permissions** y guarda.
5. Ve a la pestaña **Actions**, elige **Vigía de vacantes** y pulsa **Run workflow** para la primera corrida (la línea base). Tarda entre 5 y 15 minutos.
6. Los resultados quedan en la carpeta `salida/` del repositorio. Abre `reporte.html` y pulsa **Download raw file** para verlo.

**Para que el Radar se actualice solo (opcional):** si el repositorio es público, activa **Settings → Pages** (rama `main`, carpeta raíz). Abre el Radar desde `https://TU-USUARIO.github.io/radar-vigia/radar/progresso-radar-v2.html`: cargará las vacantes detectadas sin hacer nada. Con un repositorio privado, descarga `salida/radar_vacantes.json` y cárgalo en el Radar con **«Vacantes detectadas»**.

**Correo con las nuevas (opcional):** en **Settings → Secrets and variables → Actions** crea estos secretos:

| Secreto | Ejemplo con Gmail |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PUERTO` | `587` |
| `SMTP_USUARIO` | `tu.cuenta@gmail.com` |
| `SMTP_CLAVE` | una *contraseña de aplicación* de Google, no tu contraseña normal |
| `CORREO_DESTINO` | a quién llega el aviso |

## Opción B · En tu computador

1. Instala Python 3.10 o más reciente desde [python.org](https://www.python.org/downloads/). En Windows, marca «Add Python to PATH».
2. Abre una terminal en esta carpeta y ejecuta una sola vez:
   ```
   pip install -r requirements.txt
   ```
3. Para cada revisión:
   ```
   python vigia.py
   ```
4. Abre `salida/reporte.html` en el navegador.

Pruebas rápidas: `python vigia.py --categoria ONU` o `python vigia.py --limite 20`.
Para que corra solo: Programador de tareas (Windows) o `cron` (Mac/Linux).

---

## Ajustes en `config.yaml`

- **`perfil.palabras_clave`**: lo que debe resaltar (cargo, país, tema). Ajústalo por cliente o por ruta. Para varios clientes, haz una copia de la carpeta por cliente o usa `--config cliente.yaml --estado datos/cliente.json --salida salida/cliente`.
- **`perfil.excluir`**: lo que nunca quieres ver.
- **`terminos_portales_grandes`**: en portales Workday con más de 200 vacantes (por ejemplo, Cruz Roja Americana) solo se buscan estos términos.
- **`render_js: true`**: abre con un navegador las páginas que cargan sus vacantes con JavaScript. Es más lento; actívalo si el reporte muestra muchas en «Carga con JavaScript».
- **`organizaciones_extra`**: agrega sitios que no están en el Radar (por ejemplo, Terreno).

## Límites honestos

- El detector de páginas propias es heurístico: puede colarse algún enlace que no es vacante o escaparse una vacante con un título poco común. La comparación diaria reduce el ruido, porque solo se reporta lo que cambia.
- No abre los PDF: detecta el enlace al PDF y su título, no su contenido.
- Los sitios cambian su diseño. Si una organización pasa a «Error» varios días, revisa que su página de vacantes siga siendo la misma en `organizaciones.json`.
- Las pruebas incluidas (`tests/`) usan páginas simuladas y la estructura real de la página de convocatorias de Fundación Natura. La primera corrida real mostrará qué sitios necesitan ajuste.

## Actualizar la lista de organizaciones

`organizaciones.json` sale del Radar (campos: `id`, `n` nombre, `j` página de vacantes, `t` categoría, `afe`). Los `id` coinciden con los del Radar: así cada vacante aparece en la ficha correcta. Si cambias el Radar, regenera este archivo con los mismos `id`.
