import pandas as pd
import os
import pytest

# Import the function to be tested
from pipa.common.export import export_dataframe_to_csv


# Define a sample function to be decorated
def process_data():
    data = {"Name": ["John", "Jane", "Mike"], "Age": [25, 30, 35]}
    return pd.DataFrame(data)


# Define test cases
def test_export_dataframe_to_csv():
    # Create a temporary output file path for testing
    temp_output_filepath = "data/out/test_output.csv"
    os.makedirs("data/out", exist_ok=True)

    # Decorate the sample function with the export_dataframe_to_csv decorator
    @export_dataframe_to_csv(filepath=temp_output_filepath)
    def decorated_process_data():
        return process_data()

    # Call the decorated function
    result = decorated_process_data()

    # Assert that the result is the same as the original function's result
    assert result.equals(process_data())

    # Assert that the output file exists
    assert os.path.exists(temp_output_filepath)

    # Assert that the output file is a CSV file
    assert temp_output_filepath.endswith(".csv")

    # Assert that the output file is not empty
    assert os.path.getsize(temp_output_filepath) > 0

    # Clean up the temporary output file
    os.remove(temp_output_filepath)
    os.rmdir("data/out")


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])
