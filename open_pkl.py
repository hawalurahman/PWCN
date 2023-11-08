import pickle

with open('state_dict/pwcn_dep_restaurant.pkl', 'rb') as f:
    data = pickle.load(f)

print(data)