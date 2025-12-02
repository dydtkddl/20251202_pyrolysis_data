from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

model = AutoModelForSequenceClassification.from_pretrained("saved_model")
tokenizer = AutoTokenizer.from_pretrained("saved_model")

def predict(text):
    enc = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    logits = model(**enc).logits
    pred = torch.argmax(logits, dim=1).item()
    return "exp" if pred == 1 else "noexp"

print(predict("Pyrolysis of PP at 600°C in a fixed-bed reactor"))
print(predict("Synthesis of TiO2 nanoparticles by sol-gel"))


