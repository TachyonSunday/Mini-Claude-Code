#!/usr/bin/env python3
"""Train a fix-type classifier on 2000 CodeXGLUE Python samples."""

import json
import os
import pickle
import sys
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def extract_features(code: str) -> str:
    """Extract structural features from code."""
    tokens = re.findall(r'[A-Za-z_]\w*|[+\-*/<>=!&|^~]+|[0-9]+|[(){}\[\]]', code)
    # Keep all meaningful tokens
    filtered = [t for t in tokens if len(t) > 1 and not t.isdigit()]
    return ' '.join(filtered)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Load data
    src = os.path.join(DATA_DIR, "codexglue_py_deobfuscated.jsonl")
    if not os.path.exists(src):
        print(f"Data not found: {src}")
        sys.exit(1)

    texts = []
    labels = []
    with open(src, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                texts.append(extract_features(item.get("deobfuscated_buggy", item["python_buggy"])))
                labels.append(item["fix_type"])

    print(f"Loaded {len(texts)} samples")
    print(f"Label distribution:")
    from collections import Counter
    for label, count in Counter(labels).most_common():
        print(f"  {label}: {count} ({count/len(labels)*100:.1f}%)")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    # Vectorize
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=2000,
        sublinear_tf=True,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Train classifier
    model = LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        random_state=42,
    )
    model.fit(X_train_vec, y_train)

    # Evaluate
    train_acc = model.score(X_train_vec, y_train)
    test_acc = model.score(X_test_vec, y_test)
    cv_scores = cross_val_score(model, X_train_vec, y_train, cv=5)
    y_pred = model.predict(X_test_vec)

    print(f"\n=== Results ===")
    print(f"Train accuracy: {train_acc:.3f}")
    print(f"Test accuracy:  {test_acc:.3f}")
    print(f"5-fold CV:      {cv_scores.mean():.3f} (±{cv_scores.std():.3f})")
    print(f"\n{classification_report(y_test, y_pred)}")

    # Save
    with open(os.path.join(MODEL_DIR, "vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)
    with open(os.path.join(MODEL_DIR, "classifier.pkl"), "wb") as f:
        pickle.dump(model, f)

    print(f"Model saved to {MODEL_DIR}/")

    # Show top features per class
    feature_names = vectorizer.get_feature_names_out()
    print("\n=== Top features per class ===")
    for i, cls in enumerate(model.classes_):
        coef = model.coef_[i]
        top_idx = np.argsort(coef)[-5:][::-1]
        features = [f"{feature_names[j]}({coef[j]:.2f})" for j in top_idx]
        print(f"  {cls}: {' | '.join(features)}")


if __name__ == "__main__":
    main()
