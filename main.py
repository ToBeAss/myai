from maritime_parser import Chapter3Parser
from chroma_wrapper import Chroma_Wrapper
import re

# Load all Chapter 3 paragraphs (§ 13 - § 164) from the maritime regulations
parser = Chapter3Parser("api/sf-20210210-0523.xml")
all_paragraphs = parser.get_all()

# Format paragraphs and extract IDs from paragraph numbers
maritime_paragraphs = [parser.format(para) for para in all_paragraphs]
# Extract numeric ID from paragraph number (e.g., "§ 113" -> "113")
maritime_ids = [re.search(r'\d+', para['number']).group() for para in all_paragraphs]

# Embed and store in ChromaDB
chroma = Chroma_Wrapper(parent_dir="api", agent_name="Sjøtrafikkforskriften", embedding_model_name="openai-text-embedding-3-large")
chroma.add_text_chunks(maritime_paragraphs, ids=maritime_ids, print_statements=True)


def get_paragraphs_by_route(route_description: str, k: int = 5, score_threshold: float = 0.2) -> list[dict]:
    """Retrieve relevant maritime regulation paragraphs based on a route description.
        Arguments:
            route_description (str): Description of the maritime route.
            k (int): Number of top relevant paragraphs to retrieve.
            score_threshold (float): Minimum relevance score threshold.
        Returns:
                list: A list of dictionaries containing paragraph details and relevance scores.
    """
    result = chroma.retrieve_data_using_similarity_scores(query=route_description, k=k, score_threshold=score_threshold)

    paragraphs = []

    for embedding in result:
        paragraph = {
            "id": embedding[0].id,
            "subchapter": "",
            "title": "",
            "content": embedding[0].page_content,
            "relevance_score": embedding[1]
        }
        paragraphs.append(paragraph)
        
    return paragraphs

# [MANUAL] Extract titles from 'seilingsbeskrivelser' (route descriptions)
query="""
Sauda - Skudefjorden Inbound
Hylsfjorden'
Innseiling til Kvitsøy fra N og E'
Innseiling til Kvitsøy fra SE og S'
Makrelleia'
Nedstrandsfjorden'
Nevøysundet'
Revingssundet'
Sandsfjorden'
Saudafjorden'
Straumbergsundet'
Økstrafjorden' """
print(f"🔎 Søker med seilingsbeskrivelse-titler:{query}")
paragraphs = get_paragraphs_by_route(route_description=query, k=10, score_threshold=0.2)
print("🛠️ Resultat:")
print(paragraphs)
print()