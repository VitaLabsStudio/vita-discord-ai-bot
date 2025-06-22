import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, PodSpec

def clear_and_recreate_pinecone_index():
    """
    Deletes and then re-creates the Pinecone index to ensure it's empty and fresh, unless it already exists with the correct dimension (1536) and is empty.
    """
    load_dotenv()

    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    # This environment variable may be needed for legacy pod-based indexes
    pinecone_env = os.getenv("PINECONE_ENVIRONMENT") 

    embedding_dimension = 1536  # For OpenAI ada-002

    if not api_key or not index_name:
        print("Error: PINECONE_API_KEY and PINECONE_INDEX_NAME must be set in your .env file.")
        return

    print("Initializing Pinecone...")
    pc = Pinecone(api_key=api_key)
    
    # Check if the index exists and get its stats
    if index_name in pc.list_indexes().names():
        print(f"Found existing index '{index_name}'.")
        index = pc.Index(index_name)
        recreate_index = False
        try:
            stats = index.describe_index_stats()
            print(f"Index stats: {stats}")
            vector_count = stats.get('total_vector_count', 0)
            existing_dimension = stats.get('dimension', 0)

            if existing_dimension != embedding_dimension:
                print(f"CRITICAL: Index dimension is {existing_dimension}, but the required dimension is {embedding_dimension}.")
                print("The index must be recreated to match the model's requirements.")
                recreate_index = True
            elif vector_count == 0:
                print("Index has the correct dimension and is already empty. Nothing to do.")
                return
            else:
                print("Index has the correct dimension but is not empty. It will be deleted and recreated.")
                recreate_index = True

        except Exception as e:
            print(f"Could not get index stats: {e}. Assuming it must be recreated.")
            recreate_index = True

        if not recreate_index:
            return

        # If we are here, the index exists and needs to be deleted.
        try:
            print(f"Deleting index '{index_name}'...")
            pc.delete_index(index_name)
            # Wait for deletion to complete
            while index_name in pc.list_indexes().names():
                print("Waiting for index to be deleted...")
                time.sleep(5)
            print(f"Index '{index_name}' deleted successfully.")
        except Exception as e:
            print(f"Could not delete index: {e}")
            print("Please try deleting the index manually from the Pinecone console.")
            return
    else:
        print(f"Index '{index_name}' not found. Will proceed to create it.")

    # If the index doesn't exist, or we just deleted it, create a new one.
    print(f"Creating new index '{index_name}' with dimension {embedding_dimension}...")
    try:
        spec = {
            "serverless": {
                "cloud": "aws",
                "region": "us-east-1"
            }
        }
        # If the user has a legacy pod-based environment set, use that spec.
        if pinecone_env:
            print(f"Using pod-based spec with environment: {pinecone_env}")
            spec = PodSpec(environment=pinecone_env)

        pc.create_index(
            name=index_name,
            dimension=embedding_dimension,
            metric="cosine",
            spec=spec
        )

        # Wait for creation to complete
        while not pc.describe_index(index_name).status['ready']:
            print("Waiting for index to become ready...")
            time.sleep(5)
        print(f"Index '{index_name}' created successfully and is ready.")

    except Exception as e:
        print(f"An error occurred while creating the index: {e}")
        print("\nThis might be because you have a legacy 'pod-based' Pinecone account and need to specify its environment.")
        print("If so, please add 'PINECONE_ENVIRONMENT=your_environment_name' to your .env file and try again.")
        print("You can find the environment name in your Pinecone console (e.g., 'gcp-starter', 'us-west1-gcp', etc.).")

if __name__ == "__main__":
    load_dotenv()
    index_name = os.getenv('PINECONE_INDEX_NAME', 'your_index')
    confirm = input(f"This script will check your index '{index_name}'. If it contains data, it will be DELETED and RECREATED. This is irreversible. Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_and_recreate_pinecone_index()
    else:
        print("Operation cancelled.") 