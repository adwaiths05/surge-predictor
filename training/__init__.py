"""
training/ — SurgeCast MLOps retraining package.

This package implements the full MLOps loop:
  drift.py        → Feature drift detection (PSI + KS)
  pseudo_label.py → Pseudo-label generation for production records
  train.py        → Challenger model training
  metadata.py     → Model metadata management
  promotion.py    → Champion-challenger evaluation and model promotion
"""
