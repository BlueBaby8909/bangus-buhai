import torch
import torch.nn as nn

class BangusLSTM(nn.Module):
    """LSTM forecaster for Temperature, pH, Turbidity."""

    def __init__(
        self,
        input_size: int = 3,
        lstm1_units: int = 128,
        lstm2_units: int = 64,
        dense_units: int = 32,
        output_size: int = 3,
        dropout_rate: float = 0.2,
    ):
        super().__init__()
        self.input_size = input_size
        self.lstm1_units = lstm1_units
        self.lstm2_units = lstm2_units
        self.dense_units = dense_units
        self.output_size = output_size
        self.dropout_rate = dropout_rate

        self.lstm1 = nn.LSTM(input_size, lstm1_units, batch_first=True)
        self.dropout1 = nn.Dropout(dropout_rate)
        self.lstm2 = nn.LSTM(lstm1_units, lstm2_units, batch_first=True)
        self.dropout2 = nn.Dropout(dropout_rate)
        self.fc1 = nn.Linear(lstm2_units, dense_units)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(dense_units, output_size)

    def forward(self, x):
        out, _ = self.lstm1(x)          # (batch, seq_len, lstm1_units)
        out = self.dropout1(out)
        out, _ = self.lstm2(out)        # (batch, seq_len, lstm2_units)
        out = out[:, -1, :]             # last timestep -> return_sequences=False
        out = self.dropout2(out)
        out = self.relu(self.fc1(out))
        out = self.fc2(out)             # (batch, output_size)
        return out
