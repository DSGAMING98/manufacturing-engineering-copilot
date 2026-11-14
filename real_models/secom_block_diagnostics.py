"""SECOM block-wise random-split scores and mechanism diagnostics.

This is a post-hoc diagnostic on the same UCI SECOM data; do NOT claim it
establishes causal concept drift, or describe the original test as blind.
Run: python -m real_models.secom_block_diagnostics
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score,
                             f1_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from real_models.train_real_models import fetch
from real_models.evaluate_secom_chrono import read_labels_and_timestamps
from real_models.temporal_robustness_review import fit_select

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"real_models/evidence/secom_block_diagnostics.json"
BOUNDS=(0,627,862,1097,1332,1567)

def stats(array):
    vals=np.asarray(array,dtype=float)
    return {"n":int(len(vals)),"mean":float(vals.mean()),
            "sd":float(vals.std(ddof=1)) if len(vals)>1 else 0.,
            "min":float(vals.min()),"max":float(vals.max()),
            "p2_5":float(np.quantile(vals,.025)),
            "p97_5":float(np.quantile(vals,.975))}

def auc_or_none(y,score):
    if len(np.unique(y))<2:return None
    return float(roc_auc_score(y,score))

def fixed_budget(y,scores,fraction):
    k=max(1,int(math.ceil(len(y)*fraction)))
    order=np.argsort(-scores,kind="stable")[:k]
    selected=np.zeros(len(y),dtype=int)
    selected[order]=1
    caught=int(selected[y==1].sum())
    return {"fraction":fraction,"alert_budget":k,"alerts":int(selected.sum()),
            "total_failures":int(y.sum()),"caught_failures":caught,
            "missed_failures":int(y.sum())-caught,
            "recall":caught/int(y.sum()),
            "precision":caught/k,
            "failure_f1":float(f1_score(y,selected,zero_division=0))}

def best_test_oracle(y,scores):
    # Retrospective explanatory ceiling; MUST NEVER be advertised as deployable.
    choices=np.r_[np.inf,np.unique(scores)]
    best=None
    for threshold in choices:
        pred=(scores>=threshold).astype(int)
        f1=float(f1_score(y,pred,zero_division=0))
        if best is None or (f1,threshold)>(best[0],best[1]):
            best=(f1,float(threshold),int(pred.sum()),int(pred[y==1].sum()))
    return {"retrospective_only":True,"not_selectable_for_deployment":True,
            "test_label_selected_best_f1":best[0],
            "test_label_selected_threshold":best[1] if np.isfinite(best[1]) else None,
            "alerts":best[2],"caught_failures":best[3]}

def timeblock_random_split_scores(x,y,time_rank):
    all_records=[]
    for seed in range(50):
        xdev,xtest,ydev,ytest,idxdev,idxtest=train_test_split(
            x,y,np.arange(len(y)),test_size=.2,random_state=seed,stratify=y)
        xtrain,xval,ytrain,yval=train_test_split(
            xdev,ydev,test_size=.25,random_state=seed,stratify=ydev)
        valauc,fraction,model,threshold=fit_select(xtrain,ytrain,xval,yval)
        pred=model.predict_proba(xtest)[:,1]
        all_auc=float(roc_auc_score(ytest,pred))
        early=time_rank[idxtest]<627
        late=~early
        period_only_score=early.astype(float)
        entry={"seed":seed,"overall_auc":all_auc,
               "timestamp_only_auc":float(roc_auc_score(ytest,period_only_score)),
               "early_n":int(early.sum()),"early_failures":int(ytest[early].sum()),
               "later_n":int(late.sum()),"later_failures":int(ytest[late].sum()),
               "early_auc":auc_or_none(ytest[early],pred[early]),
               "later_auc":auc_or_none(ytest[late],pred[late]),
               "early_mean_failure_score":float(pred[early].mean()),
               "later_mean_failure_score":float(pred[late].mean()),
               "early_positive_mean_score":float(pred[early & (ytest==1)].mean()),
               "early_negative_mean_score":float(pred[early & (ytest==0)].mean()),
               "later_positive_mean_score":float(pred[late & (ytest==1)].mean()),
               "later_negative_mean_score":float(pred[late & (ytest==0)].mean()),
               "block_results":[]}
        for i,(a,b) in enumerate(zip(BOUNDS[:-1],BOUNDS[1:]),1):
            mask=(time_rank[idxtest]>=a)&(time_rank[idxtest]<b)
            entry["block_results"].append({
              "block":i,"n":int(mask.sum()),"failures":int(ytest[mask].sum()),
              "auc":auc_or_none(ytest[mask],pred[mask])})
        all_records.append(entry)
        if seed%10==9:print("block-aware random seed",seed+1,flush=True)
    paired=[x for x in all_records if x["early_auc"] is not None and x["later_auc"] is not None]
    means_by_block=[]
    for j in range(5):
        values=[p["block_results"][j]["auc"] for p in all_records if p["block_results"][j]["auc"] is not None]
        means_by_block.append({"block":j+1,"defined_seeds":len(values),
                               "undefined_seeds":50-len(values),
                               "auc_stats":stats(values) if values else None})
    return {
      "protocol":"50 post-hoc stratified random 60/20/20 splits, original selection routine",
      "overall_auc":stats([p["overall_auc"] for p in all_records]),
      "early_auc":stats([p["early_auc"] for p in paired]),
      "later_auc":stats([p["later_auc"] for p in paired]),
      "paired_seeds_with_defined_auc":len(paired),
      "early_minus_late_auc":stats([p["early_auc"]-p["later_auc"] for p in paired]),
      "early_auc_above_late_count":sum(p["early_auc"]>p["later_auc"] for p in paired),
      "timestamp_only_early_indicator_auc":stats([p["timestamp_only_auc"] for p in all_records]),
      "model_mean_failure_score_early":stats([p["early_mean_failure_score"] for p in all_records]),
      "model_mean_failure_score_later":stats([p["later_mean_failure_score"] for p in all_records]),
      "period_score_mean_delta_early_minus_later":stats([p["early_mean_failure_score"]-p["later_mean_failure_score"] for p in all_records]),
      "period_score_by_class":{
        "early_failure":stats([p["early_positive_mean_score"] for p in all_records]),
        "early_pass":stats([p["early_negative_mean_score"] for p in all_records]),
        "later_failure":stats([p["later_positive_mean_score"] for p in all_records]),
        "later_pass":stats([p["later_negative_mean_score"] for p in all_records])},
      "per_block":means_by_block,
      "per_seed":all_records,
      "caution":"Each model sees examples from every time period in its training split. Block AUCs are based only on random-held-out test rows and are often unstable due to few failures."
    }

def missingness_audit(x,y,time_rank):
    source_order=np.argsort(time_rank)
    ordered=x[source_order]
    blocks=[]
    for idx,(a,b) in enumerate(zip(BOUNDS[:-1],BOUNDS[1:]),1):
        part=np.isnan(ordered[a:b])
        blocks.append({"block":idx,"n":b-a,"missing_cell_rate":float(np.mean(part)),
                       "rows_with_missing_any":float(np.mean(part.any(axis=1)))})
    cutoff=627
    period=(time_rank>=cutoff).astype(int)
    missing=np.isnan(x).astype(float)
    xtr,xtest,ytr,ytest=train_test_split(missing,period,test_size=.3,
                                        stratify=period,random_state=42)
    probe=LogisticRegression(C=1.0,max_iter=1600,solver="liblinear",random_state=42)
    probe.fit(xtr,ytr)
    p=probe.predict_proba(xtest)[:,1]
    return {
        "period_task":"first 627 vs last 940 chronological records",
        "period_proportions":{"early":float((period==0).mean()),"later":float((period==1).mean())},
        "split":"separate random stratified 70/30 for unsupervised period diagnostic only",
        "missingness_cells_over_time":blocks,
        "missing_only_classifier":{"roc_auc":float(roc_auc_score(ytest,p)),
                   "accuracy":float(accuracy_score(ytest,p>=.5)),
                   "majority_period_accuracy":float(max(ytest.mean(),1-ytest.mean()))},
        "caution":"Period separability from missing indicators is evidence of temporal input-distribution differences, not proof that SECOM failure predictions exploit them."
    }

def filtered_chronological(x,y,time_rank):
    original_order=np.argsort(time_rank)
    xx,yy=x[original_order],y[original_order]
    a,b=int(len(y)*.6),int(len(y)*.8)
    missing_fraction=np.isnan(xx[:a]).mean(axis=0)
    keep=missing_fraction<.4
    # Entirely missing columns are excluded by keep; variance filter fits TRAIN only.
    imputer=SimpleImputer(strategy="median")
    tr_imp=imputer.fit_transform(xx[:a,keep])
    variance=VarianceThreshold(threshold=1e-12).fit(tr_imp)
    keep2=np.zeros(x.shape[1],dtype=bool)
    keep2[np.flatnonzero(keep)[variance.get_support()]]=True
    xfiltered=xx[:,keep2]
    score,fraction,model,threshold=fit_select(xfiltered[:a],yy[:a],xfiltered[a:b],yy[a:b])
    prob=model.predict_proba(xfiltered[b:])[:,1]
    pred=(prob>=threshold)
    return {
        "filters":"training-period missing fraction < 40% followed by > 1e-12 training-period median-imputed variance",
        "original_features":int(x.shape[1]),"retained_features":int(keep2.sum()),
        "dropped_features":int(x.shape[1]-keep2.sum()),
        "validation_auc":score,"selected_max_features":fraction,"selected_threshold":threshold,
        "test_auc":float(roc_auc_score(yy[b:],prob)),
        "test_average_precision":float(average_precision_score(yy[b:],prob)),
        "test_failure_f1":float(f1_score(yy[b:],pred,zero_division=0)),
        "alerts":int(pred.sum()),"caught":int(pred[yy[b:]==1].sum()),
        "caution":"Exploratory post-hoc feature filtering on an already seen time-ordered holdout."
    }

def main():
    folder,archive_hash=fetch("secom")
    x=np.genfromtxt(folder/"secom.data",missing_values="NaN")
    y,timestamps=read_labels_and_timestamps(folder/"secom_labels.data")
    chronological_order=np.argsort(timestamps,kind="stable")
    time_rank=np.empty(len(y),dtype=int)
    time_rank[chronological_order]=np.arange(len(y))
    nx,ny=x[chronological_order],y[chronological_order]
    a,b=int(len(y)*.6),int(len(y)*.8)
    v_auc,feature,chrono,threshold=fit_select(nx[:a],ny[:a],nx[a:b],ny[a:b])
    testp=chrono.predict_proba(nx[b:])[:,1]
    val_pred=(testp>=threshold).astype(int)
    validation_f1=float(f1_score(ny[b:],val_pred,zero_division=0))
    oracle=best_test_oracle(ny[b:],testp)
    chronological={
      "test_n":len(ny[b:]),"test_failures":int(ny[b:].sum()),
      "validation_failures":int(ny[a:b].sum()),
      "test_auc":float(roc_auc_score(ny[b:],testp)),
      "validation_selected_threshold":threshold,
      "validation_selected_failure_f1":validation_f1,
      "validation_selected_alerts":int(val_pred.sum()),
      "validation_selected_caught":int(val_pred[ny[b:]==1].sum()),
      "fixed_alert_budgets":[fixed_budget(ny[b:],testp,z) for z in (.05,.10,.20)],
      "test_label_oracle_threshold_diagnostic":oracle,
      "oracle_f1_minus_validation_f1":oracle["test_label_selected_best_f1"]-validation_f1,
    }
    print("chronological fixed-budget and oracle",json.dumps(chronological),flush=True)
    missingness=missingness_audit(x,y,time_rank)
    print("missingness period diagnostic",missingness["missing_only_classifier"],flush=True)
    filtered=filtered_chronological(x,y,time_rank)
    print("filtered feature sensitivity",filtered,flush=True)
    random=timeblock_random_split_scores(x,y,time_rank)
    report={
      "status":"MEASURED","date":"2026-11-14",
      "dataset":"UCI SECOM","archive_sha256":archive_hash,"post_hoc":True,
      "random_split_time_block_decomposition":random,
      "missingness_time_diagnostic":missingness,
      "chronological_decision_analysis":chronological,
      "chronological_feature_filter_sensitivity":filtered,
      "limits":[
        "Exploratory tests were formulated after initial SECOM chronology and split results were known.",
        "Block-wise random split scores still involve a model trained across all periods, including periods after each test observation.",
        "Observed time variation of missingness and failure rates does not identify the causal mechanism of ROC-AUC change.",
        "Oracle test-selected threshold is a hindsight diagnostic only, not a valid policy.",
        "Only 17 failures are present in the final chronological test window."
      ]
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("SAVED",OUTPUT,flush=True)

if __name__=="__main__":main()
