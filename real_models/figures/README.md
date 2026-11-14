# Reproducible result figures

These files are generated from
`real_models/evidence/real_model_report.json` by:

```powershell
.\.venv\Scripts\python.exe -m real_models.plot_real_results
```

| Figure | Contents |
|---|---|
| Fig01 | Locked-test headline metrics with 95% percentile-bootstrap confidence intervals |
| Fig02 | Steel fault precision, recall and F1 by class |
| Fig03 | Steel fault locked-test confusion matrix |
| Fig04 | SECOM locked-test confusion matrix |
| Fig05 | Train, validation and locked-test record counts |

PNG files are intended for the README and reports. SVG files are suitable for
publication layout. CSV files expose the plotted values for independent review.
Do not edit generated outputs by hand; update the evidence report through the
training pipeline and regenerate the figures.
