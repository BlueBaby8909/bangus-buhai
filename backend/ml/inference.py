import os

# Must be set before TensorFlow is imported. Keeps startup logs limited to
# warnings/errors instead of the usual flood of build/CPU-instruction INFO
# lines; does not affect model behavior or accuracy.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import warnings
from pathlib import Path
from typing import List

import joblib
import numpy as np
import torch

from models.water_log import WaterLog
from ml.models.bangus_lstm import BangusLSTM

# ============================================================================
# Configuration
# ============================================================================

# Number of historical water-log readings the model expects per prediction.
# Must match the InputLayer batch_shape (None, 48, 3) baked into the .keras
# file, and the row count/order the scaler was fit on (Temperature, pH,
# Turbidity). Do not change this without retraining the model.
SEQ_LENGTH = 48

# Resolved relative to this file (not the process cwd), so the model loads
# correctly no matter where `uvicorn`/`python` is invoked from.
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "bangus_buhai_lstm_pytorch.pt"
SCALER_PATH = MODEL_DIR / "bangus_buhai_scaler.pkl"

# ============================================================================
# Singleton Resources
# ============================================================================

_model = None
_scaler = None


# ============================================================================
# Resource Loading
# ============================================================================

def load_resources():
    """
    Loads the trained model and scaler into memory.

    Safe to call multiple times. Raises FileNotFoundError with the exact
    expected path if either artifact is missing, and lets any underlying
    load error (e.g. an incompatible keras/scikit-learn version) propagate
    unmodified so the real cause is visible instead of being hidden behind
    a generic failure.
    """

    global _model, _scaler

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"ML model file not found at {MODEL_PATH}. "
                "Expected 'bangus_buhai_lstm_pytorch.pt' in ml/models/."
            )
        # Initialize model architecture and load state dict
        _model = BangusLSTM()
        checkpoint = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
        _model.load_state_dict(checkpoint["state_dict"])
        _model.eval()

    if _scaler is None:
        if not SCALER_PATH.exists():
            raise FileNotFoundError(
                f"Scaler file not found at {SCALER_PATH}. "
                "Expected 'bangus_buhai_scaler.pkl' in ml/models/."
            )
        _scaler = joblib.load(SCALER_PATH)


def get_model():
    if _model is None:
        load_resources()
    return _model


def get_scaler():
    if _scaler is None:
        load_resources()
    return _scaler


# ============================================================================
# Preprocessing
# ============================================================================

def logs_to_numpy(logs: List[WaterLog]) -> np.ndarray:
    """
    Converts WaterLog objects into a NumPy array.

    Shape:
        (48,3)
    """

    return np.array(
        [
            [
                log.temperature,
                log.pH,
                log.turbidity,
            ]
            for log in logs
        ],
        dtype=np.float32,
    )


def prepare_sequence(logs: List[WaterLog]) -> np.ndarray:
    """
    Creates the model input.

    Expects `logs` in chronological order (oldest -> newest); the caller
    (services/prediction_service.py) is responsible for that ordering.

    Returns:
        (1,48,3)
    """

    if len(logs) < SEQ_LENGTH:
        raise ValueError(
            f"Model requires {SEQ_LENGTH} water logs, got {len(logs)}."
        )

    scaler = get_scaler()

    data = logs_to_numpy(logs)

    # scaler.transform expects a plain (N, 3) array in the same column
    # order it was fit on (Temperature, pH, Turbidity), which logs_to_numpy
    # guarantees. sklearn emits a UserWarning here because the scaler was
    # originally fit on a named DataFrame and we pass a raw ndarray; the
    # warning is purely informational (column order, not column names,
    # is what actually drives the transform) so it's suppressed rather
    # than pulling in pandas just to silence it.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names",
            category=UserWarning,
        )
        scaled = scaler.transform(data)

    sequence = scaled[-SEQ_LENGTH:]
    sequence = np.expand_dims(sequence, axis=0)

    # Convert to PyTorch tensor
    tensor_sequence = torch.as_tensor(sequence, dtype=torch.float32)

    return tensor_sequence


# ============================================================================
# Prediction
# ============================================================================

def predict(logs: List[WaterLog]) -> dict:
    """
    Predict future Temperature, pH and Turbidity.

    Returns:
    {
        temperature,
        pH,
        turbidity
    }
    """

    model = get_model()
    scaler = get_scaler()

    sequence = prepare_sequence(logs)

    with torch.no_grad():
        prediction_scaled = model(sequence).cpu().numpy()

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names",
            category=UserWarning,
        )
        prediction = scaler.inverse_transform(prediction_scaled)

    prediction = prediction[0]

    return {
        "temperature": float(prediction[0]),
        "pH": float(prediction[1]),
        "turbidity": float(prediction[2]),
    }


# ============================================================================
# Health Check
# ============================================================================

def is_model_loaded() -> bool:
    return _model is not None and _scaler is not None