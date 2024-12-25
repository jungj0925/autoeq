import json
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Load dataset
with open("dataset.json", "r") as file:
    genre_dataset = json.load(file)

# Flatten dataset into training examples
data = []
labels = []
for broad_genre, sub_genres in genre_dataset.items():
    for sub_genre in sub_genres:
        data.append(sub_genre)
        labels.append(broad_genre)

# Split dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(data, labels, test_size=0.2, random_state=42)

# Create a pipeline with TF-IDF Vectorizer and Logistic Regression
model = Pipeline([
    ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english")),
    ("classifier", LogisticRegression(max_iter=500))
])

# Train the model
model.fit(X_train, y_train)

# Evaluate the model
y_pred = model.predict(X_test)
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Save the trained model
with open("genre_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("Model training complete. Saved to 'genre_model.pkl'.")
