# Re-importing necessary libraries and generating the DataFrame again to create the CSV file
import pandas as pd
import numpy as np

# Generate sample data for urine parameters
np.random.seed(42)

num_samples = 2000

data = {
    "urine_volume": np.random.uniform(20, 500, num_samples),  # mL
    "temperature": np.random.uniform(35.5, 38.5, num_samples),  # °C
    "turbidity": np.random.uniform(100, 900, num_samples),  # Arbitrary scale
    "red": np.random.randint(50, 255, num_samples),  # Color sensor red value
    "green": np.random.randint(50, 255, num_samples),  # Color sensor green value
    "blue": np.random.randint(50, 255, num_samples),  # Color sensor blue value
}

# Generate a target label for UTI risk (0 = Low Risk, 1 = High Risk)
# Assume high turbidity, low green values, and high temperature indicate higher UTI risk
data["uti_risk"] = np.where(
    (data["temperature"] > 37.5) | (data["turbidity"] > 700) | (data["green"] < 100), 1, 0
)

# Convert to DataFrame
df = pd.DataFrame(data)

# Save the DataFrame to a CSV file
csv_file_path = 'urine_uti_risk.csv'
df.to_csv(csv_file_path, index=False)
csv_file_path
