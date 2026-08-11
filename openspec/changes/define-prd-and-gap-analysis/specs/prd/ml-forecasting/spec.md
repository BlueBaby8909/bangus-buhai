## Purpose
This specification defines the requirements for the machine learning forecasting system, including the LSTM model and its integration for predicting water quality parameters.

## ADDED Requirements

### Requirement: LSTM Model
The system MUST use a PyTorch LSTM model (class `BangusLSTM`: LSTM(3,128) → Dropout(0.2) → LSTM(128,64) → Dropout(0.2) → Linear(64,32) → ReLU → Linear(32,3)) predicting temperature, pH, and turbidity.
#### Scenario: Model Prediction
WHEN the ML model generates predictions
THEN it MUST predict temperature, pH, and turbidity using the PyTorch BangusLSTM architecture

### Requirement: Multi-horizon Forecasting
The model MUST provide multi-horizon forecasts for 1, 2, 3, and 4 hours ahead. (Note: The current model only predicts a single point 3 hours ahead, FORECAST_HORIZON=12 steps at 15-min intervals. Multi-horizon is still a gap/requirement).
#### Scenario: Multi-horizon Output
WHEN a forecast is generated
THEN the output MUST include predictions for 1, 2, 3, and 4 hours ahead

### Requirement: Sequential Input
The model MUST take 48 sequential water logs (SEQ_LENGTH=48 at 15-minute intervals) of temperature, pH, and turbidity as input.
#### Scenario: Model Input
WHEN data is fed to the model
THEN it MUST consist of 48 sequential water logs

### Requirement: Normalization
The system MUST use MinMaxScaler normalization.
#### Scenario: Data Normalization
WHEN data is preprocessed
THEN MinMaxScaler normalization MUST be applied

### Requirement: Confidence Scoring
The confidence scoring MUST be penalized when pH is estimated (default/manual).
#### Scenario: Penalizing Confidence Score
WHEN pH data is estimated
THEN the confidence score MUST be penalized

### Requirement: Prediction Persistence
The system MUST persist predictions in the database.
#### Scenario: Saving Predictions
WHEN a prediction is generated
THEN it MUST be saved to the database

### Requirement: Strict Parameter Prediction
The system MUST NOT use soft sensors or predict additional parameters beyond temperature, pH, and turbidity.
#### Scenario: Limiting Predictions
WHEN the system operates
THEN it MUST ONLY predict temperature, pH, and turbidity

### Requirement: Backend Endpoints
The backend MUST provide a POST endpoint to create predictions and a GET endpoint to retrieve history.
#### Scenario: Accessing Backend Endpoints
WHEN interacting with the API
THEN a POST endpoint MUST create predictions and a GET endpoint MUST retrieve history

### Requirement: Data Quality Check
The system MUST reject predictions if fewer than 48 logs (SEQ_LENGTH=48) are available.
#### Scenario: Insufficient Data
WHEN less than 48 logs are available
THEN the system MUST reject generating a prediction

### Requirement: Model Artifacts
The model artifacts MUST include a `.pt` model file (PyTorch state dict format), a `.pkl` scaler file, and a metadata JSON file.
#### Scenario: Artifact Storage
WHEN model artifacts are saved or loaded
THEN they MUST consist of a `.pt` model file, a `.pkl` scaler file, and a metadata JSON file

### Requirement: Model Training
The model MUST be trained using the Adam optimizer and MSE loss, with a batch_size of 32 and early stopping patience of 10.
#### Scenario: Model Training
WHEN the model is trained
THEN it MUST use Adam, MSE loss, batch_size=32, and early stopping patience=10

### Requirement: Prediction Response Format
The prediction response MUST include temperature, pH, turbidity, predicted_for timestamp, confidence_score, and a ph_is_estimated flag.
#### Scenario: Returning Prediction Response
WHEN a prediction response is returned
THEN it MUST contain all required fields including the ph_is_estimated flag
