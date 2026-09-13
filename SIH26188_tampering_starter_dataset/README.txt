SIH26188 SYNTHETIC DOCUMENT TAMPERING STARTER DATASET

4800 images total:
- 1200 genuine
- 1200 text tampered
- 1200 photo tampered
- 1200 stamp tampered

Splits:
- 80% train
- 10% validation
- 10% test

All documents are synthetic and NOT real identity documents.
Use this only as a starter/prototype dataset.

Recommended experiment:
1. Binary classifier: genuine vs tampered.
2. Then 4-class classifier.
3. Fine-tune a pretrained ResNet18, EfficientNet-B0, or ConvNeXt-Tiny.
4. Report precision, recall, F1, confusion matrix and false-positive/false-negative rates.

For serious benchmarking, obtain an authorized research dataset such as DocTamper. The official DocTamper repository states that its dataset is restricted to non-commercial use and requires an application/password process.
