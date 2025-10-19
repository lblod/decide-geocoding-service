from string import Template
from helpers import query
from escape_helpers import sparql_escape_uri


def register_airo():
    digiteam = "https://www.vlaanderen.be/organisaties/administratieve-diensten-van-de-vlaamse-overheid/beleidsdomein-kanselarij-bestuur-buitenlandse-zaken-en-justitie/agentschap-binnenlands-bestuur/digiteam"
    query_template = Template("""
    PREFIX mu: <http://mu.semte.ch/vocabularies/core/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX airo: <https://w3id.org/airo#>
    PREFIX example: <http://www.example.org/>
    PREFIX prov: <http://www.w3.org/ns/prov#> .

    INSERT DATA{
        GRAPH <http://mu.semte.ch/graphs/ai> {
            example:DECIDe a airo:AISystem ;
                airo:isDevelopedBy $provider ;
                example:entity-extraction .
                
            $provider a airo:AIDeveloper .
            
            example:entity-extraction a airo:AIComponent, prov:Agent .
        }
    }
    """)
    query_string = query_template.substitute(
        provider=sparql_escape_uri(digiteam)
    )
    query(query_string)
