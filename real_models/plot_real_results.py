"""Create publication-ready figures from the committed observed-data report."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / 'real_models' / 'evidence' / 'real_model_report.json'
OUT = ROOT / 'real_models' / 'figures'
NAVY = '#073f70'
TEAL = '#00aaa7'
ORANGE = '#e58b2a'
LIGHT = '#dce8ef'
INK = '#183044'


def setup() -> None:
    plt.rcParams.update({
        'figure.dpi': 140, 'savefig.dpi': 220, 'font.family': 'DejaVu Sans',
        'font.size': 10, 'axes.titlesize': 13, 'axes.labelsize': 10,
        'axes.edgecolor': '#b8c7d1', 'axes.labelcolor': INK, 'text.color': INK,
        'xtick.color': '#536878', 'ytick.color': '#536878',
        'axes.spines.top': False, 'axes.spines.right': False,
    })
    OUT.mkdir(parents=True, exist_ok=True)


def save(fig, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f'{stem}.png', bbox_inches='tight', facecolor='white')
    fig.savefig(OUT / f'{stem}.svg', bbox_inches='tight', facecolor='white')
    plt.close(fig)


def metric_overview(report: dict) -> None:
    steel = report['models']['steel_fault_classifier']['locked_test']
    secom = report['models']['secom_failure_risk']['locked_test']
    labels = ['Steel\naccuracy', 'Steel\nmacro-F1', 'SECOM\nROC-AUC', 'SECOM\nbalanced accuracy']
    values = [steel['accuracy'], steel['macro_f1'], secom['roc_auc'], secom['balanced_accuracy']]
    intervals = [steel['bootstrap_95_ci']['accuracy'], steel['bootstrap_95_ci']['macro_f1'],
                 secom['bootstrap_95_ci']['roc_auc'], secom['bootstrap_95_ci']['balanced_accuracy']]
    errors = np.array([[v - lo for v, (lo, hi) in zip(values, intervals)],
                       [hi - v for v, (lo, hi) in zip(values, intervals)]])
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    bars = ax.bar(labels, values, color=[NAVY, TEAL, NAVY, TEAL], width=.66,
                  yerr=errors, capsize=5, error_kw={'ecolor': INK, 'elinewidth': 1.2})
    ax.set_ylim(0, 1.02)
    ax.set_ylabel('Score')
    ax.set_title('Locked-test model performance',
                 loc='left', fontweight='bold', pad=28)
    ax.text(0, 1.015, 'Observed manufacturing data · 95% percentile-bootstrap confidence intervals',
            transform=ax.transAxes, fontsize=9, color='#657b89', va='bottom')
    ax.grid(axis='y', color=LIGHT, linewidth=.8)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value + .025, f'{value*100:.1f}%',
                ha='center', va='bottom', fontweight='bold')
    save(fig, 'Fig01_real_model_performance')
    with (OUT / 'Fig01_real_model_performance.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['metric', 'score', 'ci95_low', 'ci95_high', 'test_n'])
        for label, value, interval, n in zip(labels, values, intervals, [steel['n'], steel['n'], secom['n'], secom['n']]):
            writer.writerow([label.replace('\n', ' '), value, interval[0], interval[1], n])


def steel_per_class(report: dict) -> None:
    data = report['models']['steel_fault_classifier']['locked_test']['per_class']
    labels = list(data)
    x = np.arange(len(labels))
    width = .24
    fig, ax = plt.subplots(figsize=(10.8, 5.2))
    for offset, metric, color in [(-width, 'precision', NAVY), (0, 'recall', TEAL), (width, 'f1', ORANGE)]:
        ax.bar(x + offset, [data[label][metric] for label in labels], width, label=metric.title(), color=color)
    ax.set_xticks(x, [label.replace('_', ' ') for label in labels], rotation=24, ha='right')
    ax.set_ylim(0, 1.05)
    ax.set_ylabel('Score')
    ax.set_title('Steel classifier performance by fault class', loc='left',
                 fontweight='bold', pad=28)
    ax.grid(axis='y', color=LIGHT, linewidth=.8)
    ax.legend(frameon=False, ncol=3, loc='lower right', bbox_to_anchor=(1, 1.015))
    save(fig, 'Fig02_steel_per_class_metrics')
    with (OUT / 'Fig02_steel_per_class_metrics.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['class', 'precision', 'recall', 'f1', 'support'])
        for label in labels:
            writer.writerow([label, data[label]['precision'], data[label]['recall'], data[label]['f1'], data[label]['support']])


def confusion(matrix, labels, title: str, stem: str) -> None:
    values = np.asarray(matrix, dtype=int)
    fig, ax = plt.subplots(figsize=(8.2, 6.8))
    image = ax.imshow(values, cmap='Blues')
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha='right')
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel('Predicted class')
    ax.set_ylabel('True class')
    ax.set_title(title, loc='left', fontweight='bold')
    cutoff = values.max() * .55
    for row in range(values.shape[0]):
        for col in range(values.shape[1]):
            ax.text(col, row, str(values[row, col]), ha='center', va='center',
                    color='white' if values[row, col] > cutoff else INK, fontweight='bold')
    fig.colorbar(image, ax=ax, fraction=.046, pad=.04, label='Records')
    save(fig, stem)
    with (OUT / f'{stem}.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['true/predicted', *labels])
        for label, row in zip(labels, values.tolist()):
            writer.writerow([label, *row])


def dataset_splits(report: dict) -> None:
    models = report['models']
    names = ['Steel Plates Faults', 'SECOM']
    splits = [models['steel_fault_classifier']['split'], models['secom_failure_risk']['split']]
    train = [item['train'] for item in splits]
    validation = [item['validation'] for item in splits]
    test = [item['test'] for item in splits]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.bar(x, train, color=NAVY, label='Train')
    ax.bar(x, validation, bottom=train, color=TEAL, label='Validation')
    ax.bar(x, test, bottom=np.array(train)+np.array(validation), color=ORANGE, label='Locked test')
    totals = np.array(train) + np.array(validation) + np.array(test)
    for i, total in enumerate(totals):
        ax.text(i, total + 35, f'{total:,} records', ha='center', fontweight='bold')
    ax.set_xticks(x, names)
    ax.set_ylim(0, max(totals) * 1.13)
    ax.set_ylabel('Observed records')
    ax.set_title('Observed dataset partitions', loc='left', fontweight='bold', pad=28)
    ax.grid(axis='y', color=LIGHT, linewidth=.8)
    ax.legend(frameon=False, ncol=3, loc='lower right', bbox_to_anchor=(1, 1.015))
    save(fig, 'Fig05_dataset_splits')
    with (OUT / 'Fig05_dataset_splits.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['dataset', 'train', 'validation', 'locked_test', 'total'])
        for name, a, b, c, total in zip(names, train, validation, test, totals):
            writer.writerow([name, a, b, c, int(total)])


def main() -> None:
    setup()
    report = json.loads(REPORT_PATH.read_text(encoding='utf-8'))
    metric_overview(report)
    steel = report['models']['steel_fault_classifier']['locked_test']
    steel_per_class(report)
    steel_labels = [label.replace('_', ' ') for label in steel['per_class']]
    confusion(steel['confusion_matrix'], steel_labels,
              'Steel fault classifier: locked-test confusion matrix', 'Fig03_steel_confusion_matrix')
    secom = report['models']['secom_failure_risk']['locked_test']
    confusion(secom['confusion_matrix'], ['Pass', 'Failure'],
              'SECOM risk model: locked-test confusion matrix', 'Fig04_secom_confusion_matrix')
    dataset_splits(report)
    print(f'Wrote publication figures to {OUT}')


if __name__ == '__main__':
    main()
