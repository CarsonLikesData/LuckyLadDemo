# RAG Integration for Lucky Lad Invoice Processor

This document explains the changes made to integrate the Retrieval-Augmented Generation (RAG) engine with the Lucky Lad Invoice Processor, and how to use the new features for handling new invoice types.

## Overview of Changes

We've implemented several improvements to help the system better handle new invoice types:

1. **RAG Engine Integration**: The system now uses the RAG engine to provide context from similar invoices when processing new ones.
2. **New Invoice Type Detection**: The system can now detect when an invoice is from a new vendor or has a format it hasn't seen before.
3. **Human Review System**: Invoices that need human attention are flagged and saved for review.
4. **Document AI Improvement**: Corrected invoices can be submitted to Document AI for retraining.
5. **Continuous Learning**: Each processed invoice improves the system's ability to handle similar invoices in the future.

## How It Works

### 1. RAG Engine Integration

The RAG engine stores embeddings of processed invoices in a vector database. When a new invoice is processed:

- The system generates an embedding for the new invoice
- It searches for similar invoices in the database
- It provides context from similar invoices to Vertex AI
- This helps Vertex AI make better decisions about field extraction and validation

### 2. New Invoice Type Detection

When processing an invoice:

- If no similar invoices are found in the RAG database, it's flagged as a new invoice type
- The system adds a note to the Vertex AI prompt to pay special attention to this invoice
- The invoice is flagged for human review
- After review and correction, it's added to the RAG database as a reference for future similar invoices

### 3. Human Review System

The `human_review_processor.py` script provides an interactive interface for reviewing flagged invoices:

```bash
# List pending reviews
python human_review_processor.py --list

# Start interactive review session
python human_review_processor.py --interactive
```

During the review process, you can:
- View the extracted data
- Make corrections to any fields
- Submit the corrected invoice to Document AI for retraining
- Update the RAG database with the corrected information

### 4. Document AI Improvement

Corrected invoices can be submitted to Document AI to improve its extraction capabilities:

- The system converts the corrected fields into Document AI's ground truth format
- It submits the original PDF along with the corrected fields to a Document AI dataset
- This dataset can be used to retrain the Document AI processor
- Over time, this improves Document AI's ability to extract data from similar invoices

### 5. Confidence Tracking

The system now tracks confidence scores for Document AI entity extraction:

- Entities with low confidence scores are flagged
- This helps identify fields that might need human review
- It also helps prioritize which invoice types need more training examples

## Configuration

The system uses these directories:

- `processed_invoices/`: Where processed invoices are stored
- `invoices_for_review/`: Where invoices flagged for human review are stored
- `vector_db/`: Where the RAG engine stores its vector database

## Best Practices

1. **Regular Reviews**: Schedule regular review sessions to process flagged invoices
2. **Retrain Document AI**: Periodically retrain your Document AI processor with the corrected examples
3. **Monitor Performance**: Track how the system performs on different invoice types over time
4. **Add Examples**: For vendors with unique formats, add multiple examples to the RAG database

## Troubleshooting

If you encounter issues:

1. **Check the vector database**: Make sure the RAG engine is properly storing and retrieving invoices
2. **Verify Document AI dataset**: Ensure your Document AI dataset is properly configured
3. **Review logs**: Check for errors in the processing logs
4. **Regenerate embeddings**: If the RAG engine is not finding similar invoices, you may need to regenerate embeddings

## Future Improvements

Potential enhancements for the future:

1. **Specialized processors**: Create separate Document AI processors for different invoice types
2. **Automated retraining**: Set up automatic retraining of Document AI based on corrected examples
3. **Confidence thresholds**: Adjust confidence thresholds based on invoice type
4. **Vendor-specific prompts**: Create specialized prompts for different vendors