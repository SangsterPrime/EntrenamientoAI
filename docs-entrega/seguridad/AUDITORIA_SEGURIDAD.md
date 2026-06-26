# Estrategia de Auditoría de Seguridad — NEXORA
### Módulo de Inteligencia Predictiva (Churn) · Parcial 3 — ITY1101

**Proyecto:** NEXORA — Autonomous Procurement Intelligence
**Equipo:** Esteban Gamboa · Julio Llauri · Joel Sangster
**Marco normativo:** Ley N° 19.628 y Ley N° 21.719 (Chile)

---

## 1. Objetivo y alcance

Esta auditoría define la estrategia de seguridad y protección de datos del nuevo
**módulo de Inteligencia Predictiva** incorporado al pipeline DataOps de NEXORA,
el cual procesa datos de comportamiento de suscriptores para predecir su
**abandono (churn)**. El alcance cubre el ciclo de vida del dato dentro del módulo:
ingesta de la cartera, entrenamiento del modelo, scoring y consumo desde el
dashboard BI.

> **Principio rector — Minimización de datos:** el modelo de IA **no requiere**
> datos identificatorios directos (nombre, RUT, correo). Opera exclusivamente
> sobre variables de comportamiento, reduciendo la superficie de riesgo.

---

## 2. Clasificación de datos sensibles

Se clasifican las variables del dataset según su naturaleza y nivel de protección
requerido. Esta clasificación está codificada en `src/preprocesamiento.py`
(`DICCIONARIO_DATOS`) y se aplica en `src/seguridad.py`.

| Variable | Descripción | Clasificación | Nivel de protección |
|---|---|---|---|
| `edad` | Edad del titular | **Dato personal** | Alto — generalización por rol |
| `anos_cliente` | Antigüedad como suscriptor | Dato operativo | Medio |
| `uso_datos_gb` | Uso de la plataforma | Dato operativo | Medio |
| `llamadas_mes` | Interacciones de soporte | Dato operativo | Medio |
| `reclamos` | N° de reclamos | Dato operativo | Medio |
| `plan_premium` | Tipo de plan | Dato comercial | Medio |
| `abandona` | Variable objetivo | Dato derivado/analítico | Medio |
| `prob_abandono` | Score del modelo | **Dato inferido sensible** | Alto — sólo roles autorizados |

**Nota sobre el `prob_abandono`:** aunque es un dato generado, una probabilidad
de abandono asociada a una persona constituye un *perfilamiento* y, por tanto,
recibe tratamiento de dato sensible (acceso restringido y trazado).

---

## 3. Marco legal aplicable (Chile)

### 3.1 Ley N° 19.628 — Protección de la Vida Privada
Norma vigente que regula el tratamiento de datos personales. NEXORA aplica sus
principios:

| Principio | Aplicación en el módulo de IA |
|---|---|
| **Finalidad** | Los datos se usan únicamente para predecir churn y accionar retención; no para otros fines. |
| **Proporcionalidad** | Sólo se recolectan variables estrictamente necesarias para el modelo (minimización). |
| **Calidad de los datos** | El pipeline valida nulos, duplicados y rangos antes de entrenar/scorear. |
| **Seguridad** | Cifrado, seudonimización y control de acceso (sección 5). |
| **Consentimiento** | El suscriptor acepta el tratamiento analítico en los términos de servicio. |

### 3.2 Ley N° 21.719 — Nueva Ley de Protección de Datos Personales
Publicada en diciembre de 2024, moderniza el régimen y crea la **Agencia de
Protección de Datos Personales**. Eleva exigencias que NEXORA adopta de forma
anticipada:

- **Base de licitud explícita** para cada tratamiento (consentimiento informado).
- **Derechos ARCO+** (Acceso, Rectificación, Cancelación, Oposición + portabilidad).
- **Decisiones automatizadas y perfilamiento:** el titular tiene derecho a no ser
  objeto de decisiones basadas *únicamente* en tratamiento automatizado. Por eso
  el score de NEXORA es una **recomendación para un humano** (equipo de retención),
  no una decisión automática vinculante.
- **Deber de reporte de brechas** a la Agencia y a los afectados.

> ⚠️ **Corrección respecto al informe del Parcial 2:** allí se citó la "Ley
> 21.663" como norma de protección de datos. La Ley 21.663 corresponde al **Marco
> de Ciberseguridad**; la ley de datos personales correcta es la **21.719**. Ambas
> son complementarias y aplican al proyecto.

---

## 4. Matriz de roles y control de acceso (RBAC)

Implementada en `src/seguridad.py` (`ROLES` + `enmascarar_para_rol`). Cada rol
recibe una **vista mínima necesaria** de los datos.

| Rol | Ver datos personales (`edad`) | Ver scoring (`prob_abandono`) | Exportar |
|---|:---:|:---:|:---:|
| **admin** | ✅ Sí | ✅ Sí | ✅ Sí |
| **analista** | ❌ Generalizada | ✅ Sí | ✅ Sí |
| **retención** | ❌ Generalizada | ✅ Sí | ❌ No |
| **auditor** | ❌ Generalizada | ❌ No | ❌ No |

- **Generalización:** los roles no privilegiados ven la edad como rango etario
  (`18-24`, `25-34`, …) — técnica de *k-anonimato* que impide reidentificar al
  titular por su edad exacta.
- **Separación de funciones:** el auditor verifica el proceso sin acceder al
  scoring ni a datos personales, evitando conflictos de interés.

---

## 5. Políticas técnicas de seguridad

| Política | Técnica aplicada | Dónde |
|---|---|---|
| **Seudonimización** | Identificadores → hash SHA-256 con sal | `seguridad.seudonimizar_id()` |
| **Generalización** | Edad → rango etario por rol | `seguridad.generalizar_edad()` |
| **Enmascaramiento en logs** | No se registran valores personales en claro | logging del pipeline |
| **Gestión de secretos** | Sal y credenciales en variables de entorno / `.env` (nunca en código), `.gitignore` | `.env.example`, `os.getenv` |
| **Cifrado en tránsito** | TLS 1.3 en API/dashboard | Reverse proxy (heredado Parcial 2) |
| **Cifrado en reposo** | AES-256 para columnas sensibles en PostgreSQL | `pgcrypto` (heredado Parcial 2) |
| **Control de acceso** | RBAC por rol + roles de BD | `seguridad.ROLES`, PostgreSQL roles |
| **Trazabilidad** | Log de entrenamiento y scoring con timestamp | `logs/*.log` |
| **Minimización** | El modelo excluye RUT/nombre/email | Diseño del dataset |

---

## 6. Gestión de incidentes y continuidad

1. **Detección:** los logs (`logs/entrenamiento.log`, `logs/scoring_pipeline.log`)
   permiten auditar accesos y anomalías por ejecución.
2. **Notificación de brechas:** ante una filtración, reporte a la Agencia de
   Protección de Datos Personales y a los afectados conforme a la Ley 21.719.
3. **Respaldos:** backup diario de la base y versionado del modelo (`models/`).
4. **Rotación de secretos:** la sal de seudonimización y las API keys se rotan
   periódicamente (proceso heredado del plan de seguridad del Parcial 2).
5. **Reentrenamiento controlado:** el modelo se versiona; un modelo defectuoso
   puede revertirse a una versión previa (rollback).

---

## 7. Riesgos residuales y mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Reidentificación por cruce de variables | Medio | Generalización + minimización de variables |
| Sesgo del modelo (p. ej. por edad) | Alto | Auditoría de equidad; la decisión final es humana |
| Fuga de secretos en el repositorio | Alto | `.gitignore`, `.env`, escaneo de secretos en CI |
| Uso indebido del scoring | Medio | RBAC + restricción de exportación + trazabilidad |
| Deriva de datos (*data drift*) | Medio | Monitoreo de métricas y reentrenamiento programado |

---

## 8. Conclusión de la auditoría

El módulo de Inteligencia Predictiva de NEXORA incorpora seguridad **por diseño**:
minimiza datos personales, seudonimiza identificadores, generaliza datos sensibles
según rol y mantiene trazabilidad completa. La estrategia se alinea con la Ley
19.628 vigente y se anticipa a las exigencias de la Ley 21.719, especialmente en
materia de **perfilamiento y decisiones automatizadas**, manteniendo siempre un
**humano en el circuito** de la decisión de retención.
