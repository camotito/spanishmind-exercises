# Catálogo Maestro de Tipologías de Ejercicios (Unidades 1-10, 27, 38)

Este catálogo define el comportamiento pedagógico, el propósito y la estructura visual de cada molde de ejercicio integrado en el sistema[cite: 1, 2].

---

## `[T1]` Clasificación y Organización en Tablas
* **Descripción:** Se presenta un banco o caja de palabras desordenadas (sustantivos, adjetivos, etc.)[cite: 1, 2]. El alumno debe clasificarlas y distribuirlas dentro de una estructura tabular limpia bajo columnas categoriales explícitas (por ejemplo: separar palabras que van con "EL" de las que van con "LA")[cite: 1, 2].
* **Propósito:** Automatizar la identificación de marcas morfológicas (como las terminaciones de género `-o`, `-a`, `-ción`, `-ma`) mediante la discriminación visual y el agrupamiento lógico[cite: 1, 2].

## `[T2]` Completar con Soporte Gráfico o Contextual
* **Descripción:** Los enunciados del ejercicio dependen completamente de un estímulo visual previo que aporta los datos necesarios[cite: 1, 2]. Puede ser un árbol genealógico, un recuadro de profesiones, un contador visual de objetos o un directorio complejo de vecinos con oficinas y pisos[cite: 1, 2]. Las frases contienen un hueco `_____` que se rellena con la información extraída del gráfico[cite: 1, 2].
* **Propósito:** Desarrollar la comprensión lectora y la transferencia de datos reales y cotidianos a estructuras gramaticales correctas (parentescos, posesivos, números ordinales o concordancia de nombres)[cite: 1, 2].

## `[T3]` Completar Espacios con Gramática Libre (Monofase o Multifase)
* **Descripción:** Frases o textos dialogados donde se eliminan elementos funcionales críticos (artículos, preposiciones, pronombres) sin ofrecer un banco de palabras de apoyo[cite: 1, 2]. Se expande para admitir múltiples huecos independientes `_____` dentro de un mismo ítem (esencial para hilos de pronombres combinados)[cite: 1, 2]. Admite el uso del carácter vacíocero `ø` si la gramática exige omitir el elemento[cite: 1, 2].
* **Propósito:** Evaluar la fluidez, la sintaxis espontánea y la colocación exacta de partículas gramaticales basándose puramente en las restricciones del contexto y la concordancia local[cite: 1, 2].

## `[T4]` Transformación Morfológica y Escritura Directa
* **Descripción:** Ejercicio de flexión oracional o léxica pura[cite: 1, 2]. Exige transformar una palabra raíz a su forma correspondiente (pasar de masculino a femenino, de singular a plural, o convertir números romanos y abreviaturas como `(1.º)` a sus letras equivalentes)[cite: 1, 2]. El estímulo origen se coloca en columnas o inline entre paréntesis justo antes del hueco de escritura[cite: 1, 2].
* **Propósito:** Fijar las reglas de la morfología flexiva y la ortografía del español, asegurando la concordancia de género y número en sintagmas nominales y numerales[cite: 1, 2].

## `[T5]` Elección Múltiple Integrada (In-line Choice)
* **Descripción:** Selección binaria o ternaria incrustada directamente en el flujo de la oración[cite: 1, 2]. Las opciones disponibles aparecen encerradas entre paréntesis y separadas estrictamente por una barra oblicua `(opción1/opción2)` sin espacios, justo en el lugar donde deben evaluarse[cite: 1, 2]. No se permiten opciones tipográficas externas (A, B, C)[cite: 1, 2].
* **Propósito:** Entrenar la discriminación rápida y el contraste directo entre variantes críticas (ej. artículo determinado vs. indeterminado, o pronombres de objeto directo vs. indirecto como *lo/le*)[cite: 1, 2].

## `[T6]` Producción Escrita Pautada a partir de Estímulos Analógicos
* **Descripción:** Formulación y escritura de cadenas sintácticas completas a partir de datos objetivos parametrizados[cite: 1, 2]. Se utiliza para traducir indicadores específicos a lenguaje natural, como la lectura de horas cronológicas expresadas en relojes analógicos o el cálculo de fórmulas comerciales de precio/cantidad[cite: 1, 2].
* **Propósito:** Mecanizar la producción de estructuras lingüísticas rígidas y funcionales (expresiones temporales, horarios, transacciones de compra) combinando precisión matemática con exactitud gramatical[cite: 1, 2].

## `[T7]` Sustitución Sintáctica y Reescritura Oracional
* **Descripción:** Se presenta una oración modelo resuelta y una lista de enunciados base[cite: 1, 2]. Cada enunciado tiene un segmento específico envuelto en etiquetas de subrayado continuo `<u>...</u>`[cite: 1, 2]. El alumno debe reescribir la frase completa en la línea inferior sustituyendo el fragmento subrayado por la estructura correspondiente (como pronombres o hiperónimos)[cite: 1, 2].
* **Propósito:** Dominar la economía del lenguaje, la elisión sintáctica y la cohesión textual mediante la sustitución correcta de complementos pesados por sus equivalentes pronominales o colectivos[cite: 1, 2].

---

> **Nota (2026-07-20):** las tipologías T8-T17 se añadieron tras digitalizar el libro completo (126 unidades) -- el catálogo original (T1-T7) se había definido usando solo 12 de las 126 unidades y no cubría patrones reales frecuentes (completar con banco de palabras adaptadas, ordenar segmentos, combinar/reescribir oraciones, emparejamiento en columnas, clasificación en tabla, enumeración abierta, acentuación directa sobre la palabra). Ver `libro_pipeline/clasificar_otros.py` para el criterio de asignación.

## `[T8]` Completar con Banco de Palabras Adaptadas
* **Descripción:** Se ofrece un conjunto compartido de opciones (verbos en infinitivo, adjetivos, expresiones...) -- en un recuadro visual o enumeradas en el propio enunciado -- y el alumno debe elegir la adecuada para cada hueco y adaptarla (conjugarla, concordarla en género/número) al contexto de la frase.
* **Propósito:** Entrenar la selección léxica contextual junto con la flexión morfológica correcta, sin la ambigüedad de un hueco totalmente libre ni la rigidez de un estímulo fijo por hueco.

## `[T9]` Ordenar Palabras o Segmentos Dados
* **Descripción:** Se presentan las palabras o segmentos de una frase desordenados (a menudo separados por barras oblicuas) y el alumno debe reescribirlos en el orden correcto, a veces completando además alguna parte de la frase.
* **Propósito:** Practicar el orden sintáctico correcto de la oración en español (posición del verbo, pronombres, adjetivos...) de forma explícita.

## `[T10]` Combinar Dos Oraciones en Una
* **Descripción:** Se presentan dos oraciones independientes y el alumno debe unirlas en una sola oración usando el conector, relativo o estructura gramatical indicada (en el enunciado o entre paréntesis), realizando los cambios sintácticos necesarios.
* **Propósito:** Practicar la subordinación y coordinación de oraciones, y el manejo de nexos (relativos, causales, concesivos, consecutivos...) en producción libre.

## `[T11]` Reescribir una Oración Transformada
* **Descripción:** Se da una oración completa y el alumno debe reescribirla entera aplicando una transformación indicada: cambiar a forma negativa, insertar una expresión en un punto marcado, corregir un error, adaptar mayúsculas...
* **Propósito:** Practicar una transformación gramatical u ortográfica concreta sobre una oración ya construida, reforzando la reestructuración completa en vez de un hueco puntual.

## `[T12]` Producción Libre desde una Situación
* **Descripción:** A partir de una situación, dato o pregunta (sin una oración base que transformar o combinar), el alumno redacta una frase o respuesta nueva -- una pregunta, una respuesta de diálogo, una transformación a estilo indirecto, un deseo, una queja...
* **Propósito:** Practicar la producción espontánea guiada, más abierta que T10/T11 porque no parte de una oración ya escrita que transformar, sino de un contexto o dato.

## `[T13]` Emparejamiento en Columnas
* **Descripción:** Dos (o tres) columnas de elementos -- inicios y finales de frase, preguntas y respuestas, siglas y nombres -- que el alumno debe relacionar correctamente, a veces escribiendo después la oración completa resultante.
* **Propósito:** Practicar el reconocimiento de qué elementos combinan correctamente (léxica o gramaticalmente) antes o en vez de producir la oración desde cero.

## `[T14]` Clasificación en Tabla
* **Descripción:** Un banco de palabras o datos debe repartirse en las categorías de una tabla (columnas con encabezado, pares correspondientes, o una escala ordenada), en vez de rellenar huecos en frases.
* **Propósito:** Practicar la categorización gramatical (género, mayor/menor frecuencia...) de forma visual y agrupada.

## `[T15]` Enumeración Abierta desde un Gráfico
* **Descripción:** A partir de un dibujo o situación compartida, el alumno continúa una enumeración con un número de respuestas no fijado de antemano (cuenta y nombra lo que observa).
* **Propósito:** Practicar vocabulario y estructuras de cantidad/enumeración en un contexto abierto, no acotado a un número fijo de huecos.

## `[T16]` Anotación Directa sobre la Palabra
* **Descripción:** El alumno marca o modifica directamente las palabras ya impresas (subrayar la sílaba tónica, añadir una tilde, dividir en sílabas), sin un hueco '_____' independiente.
* **Propósito:** Practicar reglas de acentuación y silabeo trabajando sobre la propia palabra, no sobre una frase con hueco.
