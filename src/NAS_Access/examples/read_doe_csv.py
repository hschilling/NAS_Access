import numpy as np
import csv

number_doe = 4
output_filepath = 'Output/doe.csv'

output = np.zeros(number_doe)

with open(output_filepath, 'rb') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        print(i,row['Vane4_bx'])
        output[i] = row['Vane4_bx']

print output

