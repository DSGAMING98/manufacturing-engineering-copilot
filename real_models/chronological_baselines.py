"""Post-hoc chronological SECOM baseline study with validation-only selection.

Original chronological split is retained exactly: earliest 60% training,
next 20% validation, last 20% historical holdout. Comparisons are exploratory,
since the chronological holdout result is already public. No new plant data.
Run: python -m real_models.chronological_baselines
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             balanced_accuracy_score, f1_score, confusion_matrix)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from real_models.train_real_models import fetch
from real_models.evaluate_secom_chrono import read_labels_and_timestamps

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"real_models/evidence/chrono_baseline_report.json"

def candidate_sets():
    scaler=lambda estimator: make_pipeline(SimpleImputer(strategy="median"),
                                          StandardScaler(),estimator)
    return {
        "logistic_regression": [(f"C={c}", scaler(LogisticRegression(
           C=c, max_iter=1600, class_weight="balanced", random_state=42))) for c in (.1, 1., 10.)],
        "rbf_svm": [(f"C={c}", scaler(SVC(C=c, kernel="rbf",
           class_weight="balanced", probability=True, random_state=42))) for c in (.1, 1., 10.)],
        "knn": [(f"n_neighbors={k}", scaler(KNeighborsClassifier(
           n_neighbors=k))) for k in (5, 11, 21)],
        "gradient_boosting": [(f"n_estimators={k}", make_pipeline(
           SimpleImputer(strategy="median"),
           GradientBoostingClassifier(n_estimators=k, random_state=42))) for k in (60,100,150)],
        "extra_trees_released_family": [(f"max_features={f}", make_pipeline(
           SimpleImputer(strategy="median"),
           ExtraTreesClassifier(n_estimators=600, max_features=f, class_weight="balanced",
                               random_state=42,n_jobs=-1))) for f in ("sqrt", .3, .5)]
    }

def choose_threshold(y, scores):
    # Mirrors released threshold selection; never consult chronological holdout.
    return float(max(np.unique(scores), key=lambda t:(f1_score(y,scores>=t,zero_division=0),t)))

def scores_for(y, scores, threshold):
    pred=(scores>=threshold).astype(int)
    return {
       "roc_auc":float(roc_auc_score(y,scores)),
       "average_precision":float(average_precision_score(y,scores)),
       "balanced_accuracy":float(balanced_accuracy_score(y,pred)),
       "failure_f1":float(f1_score(y,pred,zero_division=0)),
       "failure_recall":float((pred[y==1]==1).mean()),
       "confusion_matrix":confusion_matrix(y,pred,labels=(0,1)).tolist(),
       "predicted_failures":int(pred.sum()),
    }

def bootstrap_ci(y, prob, n=1000, seed=20261114):
    rng=np.random.default_rng(seed)
    measures={"roc_auc":[],"average_precision":[]}
    for i in range(n):
        ids=rng.integers(0,len(y),len(y))
        if len(set(y[ids]))<2:continue
        measures["roc_auc"].append(float(roc_auc_score(y[ids],prob[ids])))
        measures["average_precision"].append(float(average_precision_score(y[ids],prob[ids])))
    return {k:[float(v) for v in np.percentile(val,(2.5,97.5))] for k,val in measures.items()}

def main():
    folder, sha=fetch("secom")
    x=np.genfromtxt(folder/"secom.data", missing_values="NaN")
    y,times=read_labels_and_timestamps(folder/"secom_labels.data")
    order=np.argsort(times,kind="stable")
    x,y=x[order],y[order]
    a,b=int(len(y)*.6),int(len(y)*.8)
    tr,v,t=(slice(0,a),slice(a,b),slice(b,len(y)))
    output={
      "context":"retrospective post-hoc analysis; previously inspected timestamp-sorted holdout",
      "source_sha256":sha,
      "chronological_split":{"train":len(y[tr]),"validation":len(y[v]),"test":len(y[t]),
                            "failures":{"train":int(y[tr].sum()),
                            "validation":int(y[v].sum()),"test":int(y[t].sum())}},
      "methods":{},"bootstrap_method":"1000 row-resampled percentile intervals; ignores temporal correlation"
    }
    # Unambiguous constant baselines; deliberately no tuned threshold on constant scores.
    for label, prediction in (("always_pass",0),("always_failure",1)):
        test_scores=np.zeros(len(y[t]),dtype=float)
        outcome=scores_for(y[t],test_scores,-.5 if prediction==1 else .5)
        outcome["bootstrap_95_ci"]=bootstrap_ci(y[t],test_scores)
        output["methods"][label]={
            "chosen_hyperparameters":"no training; fixed constant decision",
            "threshold":"all-failure" if prediction else "all-pass",
            "test":outcome
        }
        print(label,round(outcome["roc_auc"],4),round(outcome["failure_f1"],4),flush=True)

    for name,configs in candidate_sets().items():
        best=None
        for setting,model in configs:
            model.fit(x[tr],y[tr])
            valprob=model.predict_proba(x[v])[:,1]
            val_auc=float(roc_auc_score(y[v],valprob))
            if best is None or val_auc>best[0]:
                best=(val_auc,setting,model,valprob)
        val_auc,chosen,model,valp=best
        threshold=choose_threshold(y[v],valp)
        testp=model.predict_proba(x[t])[:,1]
        metrics=scores_for(y[t],testp,threshold)
        metrics["bootstrap_95_ci"]=bootstrap_ci(y[t],testp)
        output["methods"][name]={
          "validation_auc":val_auc,"selected_hyperparameter":chosen,
          "validation_selected_failure_f1_threshold":threshold,
          "test":metrics}
        print(name,"selected",chosen,"ROC-AUC",round(metrics["roc_auc"],4),
              "AP",round(metrics["average_precision"],4),
              "F1",round(metrics["failure_f1"],4),flush=True)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print("saved",DEST)

if __name__=="__main__":
    main()
