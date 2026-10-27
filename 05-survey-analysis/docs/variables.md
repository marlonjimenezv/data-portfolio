# Variables used (data dictionary)

Source: *GSS 2024 Codebook, Release 3a* (NORC), included in the official download. Question wording is quoted
from the codebook. "Don't know", "no answer", "skipped on web" and similar codes are treated as missing.

| GSS variable | Question / meaning (codebook) | Coding in this analysis |
|---|---|---|
| `HAPPY` | "Taken all together, how would you say things are these days--would you say that you are very happy, pretty happy, or not too happy?" | 3 categories; outcome of the regression: 1 = very happy, 0 = pretty or not too happy |
| `MARITAL` | "Are you currently married, widowed, divorced, separated, or have you never been married?" | Married / Never married / Divorced or separated / Widowed |
| `HEALTH` | "Would you say your own health, in general, is excellent, good, fair, or poor?" | Excellent / Good / Fair / Poor |
| `SATFIN` | "We are interested in how people are getting along financially these days. So far as you and your family are concerned, would you say that you are pretty well satisfied with your present financial situation, more or less satisfied, or not satisfied at all?" | Satisfied / More or less satisfied / Not satisfied at all |
| `AGE` | Respondent's age (89 = 89 or older) | 18-34 / 35-49 / 50-64 / 65+ |
| `SEX` | Respondent's sex | Male / Female |
| `DEGREE` | Respondent's highest degree | Bachelor's or higher (codes 3-4) vs no bachelor's degree (codes 0-2) |
| `ATTEND` | "How often do you attend religious services?" | Monthly or more (codes 4-8: about once a month or more often) vs less than monthly (codes 0-3) |
| `WTSSNRPS_AS` | Post-stratification and nonresponse weight for analysing GSS 2024 with the AmeriSpeak oversample | Survey weight for every estimate (all 3,986 cases) |
| `VSTRAT`, `VPSU` | Variance stratum and primary sampling unit | Design variables for the standard errors (68 strata, 137 PSUs) |

**Weight choice.** NORC's *GSS 2024 - What's New (R3a)* explains that `WTSSNRPS_AS` was created so that the 677
AmeriSpeak cases can be analysed together with the other respondents; it is the only weight defined for all 3,986
cases.
