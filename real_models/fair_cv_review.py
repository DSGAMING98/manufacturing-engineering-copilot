"""Supplement: equalized small-grid baseline tuning and released-estimator CV.

Uses the original 60/20/20 splits and *already reported* holdouts.
All candidate hyperparameters are selected on the original validation split.
Repeated 3x2 stratified CV on development records is descriptive only because
the candidates were chosen using part of that development pool.

Run: python -m real_models.fair_cv_review --cv-folds 3 --cv-repeats 2
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score,roc_auc_score,accuracy_score,balanced_accuracy_score,average_precision_score
from sklearn.model_selection import RepeatedStratifiedKFold,cross_val_score,train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from real_models.train_real_models import fetch

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"real_models/evidence/fair_cv_review.json"

def candidates(task):
    scale=lambda m:make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),m)
    models={
       "logistic_regression":[(f"C={c}",scale(LogisticRegression(C=c,max_iter=1600,class_weight="balanced",random_state=42))) for c in (.1,1.,10.)],
       "rbf_svm":[(f"C={c}",scale(SVC(C=c,kernel="rbf",probability=True,class_weight="balanced",random_state=42))) for c in (.1,1.,10.)],
       "knn":[(f"k={n}",scale(KNeighborsClassifier(n_neighbors=n))) for n in (5,11,21)],
       "gradient_boosting":[(f"n_estimators={n}",make_pipeline(SimpleImputer(strategy="median"),GradientBoostingClassifier(n_estimators=n,random_state=42))) for n in (60,100,150)],
    }
    if task=="steel":
       models["released_random_forest"]=[("max_depth=12",RandomForestClassifier(n_estimators=300,max_depth=12,class_weight="balanced_subsample",max_features="sqrt",random_state=42,n_jobs=-1))]
    else:
       models["released_extra_trees"]=[("max_features=0.3",make_pipeline(SimpleImputer(strategy="median"),ExtraTreesClassifier(n_estimators=600,max_features=.3,class_weight="balanced",random_state=42,n_jobs=-1)))]
    return models

def split(x,y):
    xd,xt,yd,yt=train_test_split(x,y,test_size=.2,random_state=42,stratify=y)
    xtr,xv,ytr,yv=train_test_split(xd,yd,test_size=.25,random_state=42,stratify=yd)
    return (xd,xt,yd,yt,xtr,xv,ytr,yv)

def analyze(task,x,y,folds,repeats):
    xd,xt,yd,yt,xtr,xv,ytr,yv=split(x,y)
    metric="f1_macro" if task=="steel" else "roc_auc"
    cv=RepeatedStratifiedKFold(n_splits=folds,n_repeats=repeats,random_state=42)
    findings={}
    predicted_test_labels={}
    for name,options in candidates(task).items():
        scored=[]
        for setting,model in options:
            model.fit(xtr,ytr)
            if task=="steel":
                score=float(f1_score(yv,model.predict(xv),average="macro"))
            else:
                score=float(roc_auc_score(yv,model.predict_proba(xv)[:,1]))
            scored.append((score,setting,model))
        valid_score,choice,model=max(scored,key=lambda item:item[0])
        # Refit on original train (not train+validation), so holdout result
        # can be compared with originally released models on their own protocol.
        scores=cross_val_score(model,xd,yd,cv=cv,scoring=metric,n_jobs=1,error_score="raise")
        if task=="steel":
            pred=model.predict(xt)
            outcome={"accuracy":float(accuracy_score(yt,pred)),
                     "macro_f1":float(f1_score(yt,pred,average="macro"))}
        else:
            valp=model.predict_proba(xv)[:,1]
            cutoff=float(max(np.unique(valp),key=lambda t:(f1_score(yv,valp>=t,zero_division=0),t)))
            prob=model.predict_proba(xt)[:,1]
            pred=(prob>=cutoff)
            outcome={"roc_auc":float(roc_auc_score(yt,prob)),
                     "average_precision":float(average_precision_score(yt,prob)),
                     "balanced_accuracy":float(balanced_accuracy_score(yt,pred)),
                     "failure_f1":float(f1_score(yt,pred,zero_division=0)),
                     "threshold":cutoff}
        predicted_test_labels[name]=np.asarray(pred,dtype=int)
        findings[name]={"candidate_count":len(options),"selected":choice,
              "validation_selection_score":valid_score,
              "cv_mean":float(np.mean(scores)),
              "cv_sd":float(np.std(scores,ddof=1)),
              "existing_holdout":outcome}
        print(task,name,choice,"cv",round(float(np.mean(scores)),4),
              "holdout",json.dumps(outcome),flush=True)
    reference_name="released_random_forest" if task=="steel" else "released_extra_trees"
    reference=predicted_test_labels[reference_name]
    for method,prediction in predicted_test_labels.items():
        if method==reference_name:
            continue
        ref_correct=(reference==yt)
        other_correct=(prediction==yt)
        n_ref_only=int((ref_correct & ~other_correct).sum())
        n_other_only=int((other_correct & ~ref_correct).sum())
        n_discordant=n_ref_only+n_other_only
        pval=float(binomtest(min(n_ref_only,n_other_only),n_discordant,0.5).pvalue) if n_discordant else 1.0
        findings[method]["paired_mcnemar"]={
            "incumbent_only_correct":n_ref_only,
            "baseline_only_correct":n_other_only,
            "discordant":n_discordant,
            "exact_two_sided_p":pval,
            "interpretation":"unadjusted paired classification correctness; not a test of F1 or ROC-AUC"}
    return {"metric":metric,"development_n":len(xd),"holdout_n":len(yt),
            "results":findings,"protocol":{
                "cv_folds":folds,"cv_repeats":repeats,
                "selection":"original train/validation only; no test-set tuning",
                "cv_limitation":"CV scores are not fully nested: selected settings saw original validation subset inside development pool",
                "holdout_limitation":"original test partition already reported in earlier release; comparisons are post-hoc",
                "baseline_grids":"C (.1,1,10); neighbors (5,11,21); boosting trees (60,100,150)",
                "released_model_cv":"fixed originally released setting evaluated across repeated development CV folds"
            }}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cv-folds",type=int,default=3)
    p.add_argument("--cv-repeats",type=int,default=2)
    args=p.parse_args()
    sfolder,shash=fetch("steel")
    m=np.loadtxt(sfolder/"Faults.NNA")
    steel=analyze("steel",m[:,:27],m[:,27:].argmax(axis=1),args.cv_folds,args.cv_repeats)
    efolder,ehash=fetch("secom")
    x=np.genfromtxt(efolder/"secom.data",missing_values="NaN")
    y=(np.loadtxt(efolder/"secom_labels.data",usecols=0).astype(int)==1).astype(int)
    secom=analyze("secom",x,y,args.cv_folds,args.cv_repeats)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps({"purpose":"post-hoc fairer configurations and released-estimator CV",
                                 "data_sha256":{"steel":shash,"secom":ehash},
                                 "steel":steel,"secom":secom},indent=2)+"\n",encoding="utf-8")
    print("saved",DEST)
if __name__=="__main__":main()
