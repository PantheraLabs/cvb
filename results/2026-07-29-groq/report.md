# CVB Report

## Headline: strict accuracy by arm

| model | cold | mandated | incentivized | gap (mandated - incentivized) |
| --- | --- | --- | --- | --- |
| llama-3.1-8b-instant | 0.229 | 0.914 | 0.857 | 0.057 |
| llama-3.3-70b-versatile | 0.229 | 0.952 | 0.981 | -0.029 |
| openai/gpt-oss-120b | 0.638 | 0.962 | 0.952 | 0.010 |

## llama-3.1-8b-instant by category (strict accuracy)

| category | cold | mandated | incentivized |
| --- | --- | --- | --- |
| concurrency | 0.200 | 1.000 | 0.800 |
| encoding-io | 0.200 | 0.800 | 0.800 |
| error-handling | 0.000 | 1.000 | 0.800 |
| library-choice | 0.400 | 1.000 | 1.000 |
| logging-testing | 0.200 | 0.800 | 0.800 |
| security | 0.200 | 0.800 | 0.800 |
| style-architecture | 0.400 | 1.000 | 1.000 |

## llama-3.3-70b-versatile by category (strict accuracy)

| category | cold | mandated | incentivized |
| --- | --- | --- | --- |
| concurrency | 0.000 | 1.000 | 1.000 |
| encoding-io | 0.200 | 0.800 | 1.000 |
| error-handling | 0.000 | 0.867 | 0.867 |
| library-choice | 0.000 | 1.000 | 1.000 |
| logging-testing | 0.600 | 1.000 | 1.000 |
| security | 0.400 | 1.000 | 1.000 |
| style-architecture | 0.400 | 1.000 | 1.000 |

## openai/gpt-oss-120b by category (strict accuracy)

| category | cold | mandated | incentivized |
| --- | --- | --- | --- |
| concurrency | 0.800 | 1.000 | 1.000 |
| encoding-io | 0.933 | 1.000 | 1.000 |
| error-handling | 0.200 | 0.800 | 0.867 |
| library-choice | 0.400 | 0.933 | 1.000 |
| logging-testing | 0.933 | 1.000 | 0.800 |
| security | 0.600 | 1.000 | 1.000 |
| style-architecture | 0.600 | 1.000 | 1.000 |
