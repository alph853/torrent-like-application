# Define the input dictionary
data = {
    "a": [1, 0, 1, 1, 0],
    "bv": [1, 0, 1, 1, 1],
    "d": [0, 0, 1, 0, 0]
}

# Use zip to pair corresponding elements and sum them
result = {str(i): (sum(x) if sum(x)!=0 else 99 )for i, x in enumerate(zip(*data.values()))}

print(result)  # Output: {'0': 2, '1': 0, '2': 3, '3': 2, '4': 1}
