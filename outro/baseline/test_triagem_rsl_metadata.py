"""Testes basicos para a triagem de metadados da RSL."""

from triagem_rsl_metadata import ArticleMetadata, build_evidence, decide_article


def test_direct_relevant_article_is_approved_in_all_profiles() -> None:
    """Artigo claramente alinhado deve passar em todos os perfis."""

    article = ArticleMetadata(
        item_id="TEST-APPROVE",
        title="Machine learning for procurement and supply chain decisions in the petrochemical industry",
        doi="10.0000/test-approve",
        item_type="journalArticle",
        abstract=(
            "This study proposes a decision support system for procurement, inventory, and lead time "
            "prediction in a petrochemical supply chain using machine learning and predictive analytics."
        ),
        manual_tags="petrochemical; supply chain; procurement; machine learning; predictive analytics",
    )
    evidence = build_evidence(article)
    assert decide_article("conservador", article, evidence)[0] == "Aprovado"
    assert decide_article("moderado", article, evidence)[0] == "Aprovado"
    assert decide_article("abrangente", article, evidence)[0] == "Aprovado"


def test_review_article_is_rejected_in_all_profiles() -> None:
    """Estudo secundario deve ser excluido logo na triagem."""

    article = ArticleMetadata(
        item_id="TEST-REVIEW",
        title="A systematic review of AI in oil and gas supply chains",
        doi="10.0000/test-review",
        item_type="journalArticle",
        abstract="This systematic review synthesizes published studies on AI adoption in oil and gas supply chains.",
        manual_tags="systematic review; oil and gas; supply chain; artificial intelligence",
    )
    evidence = build_evidence(article)
    assert decide_article("conservador", article, evidence)[0] == "Reprovado"
    assert decide_article("moderado", article, evidence)[0] == "Reprovado"
    assert decide_article("abrangente", article, evidence)[0] == "Reprovado"


def test_off_topic_asset_article_is_rejected() -> None:
    """Tema operacional de reservatorio nao deve seguir para texto completo."""

    article = ArticleMetadata(
        item_id="TEST-OFFTOPIC",
        title="Deep learning for reservoir lithology classification while drilling",
        doi="10.0000/test-offtopic",
        item_type="conferencePaper",
        abstract="The paper predicts lithology from well-log and drilling data for reservoir characterization.",
        manual_tags="deep learning; drilling; lithology; reservoir",
    )
    evidence = build_evidence(article)
    assert decide_article("conservador", article, evidence)[0] == "Reprovado"
    assert decide_article("moderado", article, evidence)[0] == "Reprovado"
    assert decide_article("abrangente", article, evidence)[0] == "Reprovado"


def test_manual_override_is_applied() -> None:
    """Overrides manuais precisam prevalecer sobre a heuristica."""

    article = ArticleMetadata(
        item_id="A8FUAV7T",
        title="Understanding AI Application Dynamics in Oil and Gas Supply Chain Management and Development: A Location Perspective",
        doi="10.28991/HIJ-SP2022-03-01",
        item_type="journalArticle",
        abstract="A literature review approach is adopted to capture representative research along these locations.",
        manual_tags="oil and gas; supply chain; artificial intelligence; literature reviews",
    )
    evidence = build_evidence(article)
    assert decide_article("conservador", article, evidence)[0] == "Reprovado"
    assert decide_article("moderado", article, evidence)[0] == "Reprovado"
    assert decide_article("abrangente", article, evidence)[0] == "Reprovado"
