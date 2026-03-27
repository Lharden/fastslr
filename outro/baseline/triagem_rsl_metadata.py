"""Triagem inicial de metadados para RSL em O&G + IA + SCM/SCRM."""

from __future__ import annotations

import argparse
import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final


LOGGER = logging.getLogger(__name__)
PROFILES: Final[tuple[str, ...]] = ("conservador", "moderado", "abrangente")
SECTION_WEIGHTS: Final[dict[str, float]] = {"title": 3.0, "abstract": 2.0, "tags": 1.0}

PatternSpec = tuple[str, str]


def compile_specs(specs: list[PatternSpec]) -> list[tuple[str, re.Pattern[str]]]:
    """Compila expressoes regulares nomeadas."""

    return [(label, re.compile(pattern, flags=re.IGNORECASE)) for label, pattern in specs]


SECTOR_PATTERNS = compile_specs(
    [
        ("oil and gas", r"\boil(?:\s*&\s*|\s+and\s+)gas\b"),
        ("petroleum", r"\bpetroleum\b"),
        ("petrochemical", r"\bpetrochemical(?:s)?\b"),
        ("refinery", r"\brefiner(?:y|ies)\b"),
        ("crude oil", r"\bcrude oil\b"),
        ("oil company", r"\boil compan(?:y|ies)\b"),
        ("oil marketing company", r"\boil marketing compan(?:y|ies)\b"),
        ("gas station", r"\bgas stations?\b"),
        ("offshore", r"\boffshore\b"),
        ("fuel tanker", r"\bfuel tanker(?:s)?\b"),
    ]
)

SCM_STRONG_PATTERNS = compile_specs(
    [
        ("supply chain", r"\bsupply chain(?: management)?\b"),
        ("procurement", r"\bprocurement\b"),
        ("supplier", r"\bsupplier(?: selection)?\b"),
        ("vendor", r"\bvendor(?:-managed)?\b"),
        ("inventory", r"\binventory(?:[- ]routing| policy| management| control)?\b"),
        ("warehouse", r"\bwarehouse(?: management)?\b"),
        ("spare parts", r"\bspare parts?\b"),
        ("replenishment", r"\breplenishment\b"),
        ("transportation", r"\btransportation\b"),
        ("oil logistics", r"\boil logistics\b"),
        ("offshore logistics", r"\boffshore logistics\b"),
        ("petroleum logistics", r"\bpetroleum logistics\b"),
        ("supply vessel", r"\bsupply vessels?\b"),
        ("fleet sizing", r"\bfleet sizing\b"),
        ("lead time", r"\blead times?\b"),
        ("bid evaluation", r"\bbid evaluation\b"),
        ("technical bid", r"\btechnical bids?\b"),
        ("tender", r"\btender(?:ing|s)?\b"),
        ("routing", r"\brouting\b"),
        ("critical supply", r"\bcritical supply\b"),
        ("supply planning", r"\bsupply planning\b"),
        ("transportation routes", r"\btransportation routes?\b"),
        ("supply chain finance", r"\bsupply chain finance\b"),
        ("raw material procurement", r"\braw material procurement\b"),
        ("oil product transportation", r"\boil product transportation\b"),
        ("petroleum product supply", r"\bpetroleum product supply\b"),
        ("logistics service provider", r"\blogistics service providers?\b"),
        ("vehicle routing", r"\bvehicle routing\b"),
        ("transportation cost", r"\btransportation cost\b"),
        ("fleet operations", r"\bfleet operations\b"),
        ("supply chain risk", r"\bsupply chain risk\b"),
        ("supply chain resilience", r"\bsupply chain resilience\b"),
    ]
)

SCM_SUPPORT_PATTERNS = compile_specs(
    [
        ("decision support", r"\bdecision support(?: system| systems| methodology| tool| tools)?\b"),
        ("forecasting", r"\bforecast(?:ing)?\b"),
        ("data analytics", r"\bdata analytics?\b"),
        ("business intelligence", r"\bbusiness intelligence\b"),
        ("optimization", r"\boptimi[sz]\w*\b"),
        ("simulation", r"\bsimulation\b"),
        ("multi-agent", r"\bmulti-agent\b"),
        ("digital twin", r"\bdigital twin(?:s)?\b"),
    ]
)

AI_STRONG_PATTERNS = compile_specs(
    [
        ("artificial intelligence", r"\bartificial intelligence\b"),
        ("machine learning", r"\bmachine learning\b"),
        ("deep learning", r"\bdeep learning\b"),
        ("neural network", r"\bneural networks?\b"),
        ("large language model", r"\blarge language models?\b"),
        ("llm", r"\bllms?\b"),
        ("natural language processing", r"\bnatural language processing\b"),
        ("generative ai", r"\bgenerative ai\b"),
        ("reinforcement learning", r"\breinforcement learning\b"),
        ("predictive analytics", r"\bpredictive analytics\b"),
        ("transformer", r"\btransformers?\b"),
        ("data science", r"\bdata science\b"),
        ("cognitive procurement", r"\bcognitive procurement\b"),
        ("distributed ai", r"\bdistributed artificial intelligence\b"),
    ]
)

AI_SUPPORT_PATTERNS = compile_specs(
    [
        ("business intelligence", r"\bbusiness intelligence\b"),
        ("data-driven", r"\bdata[- ]driven\b"),
        ("bayesian network", r"\bbayesian networks?\b"),
        ("fuzzy", r"\bfuzzy\b"),
        ("digital twin", r"\bdigital twin(?:s)?\b"),
        ("evolutionary optimization", r"\bevolutionary (?:algorithm|algorithms|optimization)\b"),
        ("genetic algorithm", r"\bgenetic algorithms?\b"),
        ("swarm intelligence", r"\bswarm intelligence\b"),
        ("ant colony", r"\bant colony\b"),
        ("multi-agent", r"\bmulti-agent\b"),
    ]
)

EXCLUSION_PATTERNS = compile_specs(
    [
        ("systematic review", r"\bsystematic review\b"),
        ("literature review", r"\bliterature review\b"),
        ("comprehensive review", r"\bcomprehensive review\b"),
        ("critical review", r"\bcritical review\b"),
        ("review of", r"\breview of\b"),
        ("survey", r"\bsurvey\b"),
        ("overview", r"\boverview\b"),
        ("meta-analysis", r"\bmeta-analysis\b"),
        ("scientometric", r"\bscientometric\b"),
        ("bibliometric", r"\bbibliometric\b"),
        ("tutorial", r"\btutorial\b"),
        ("book chapter", r"\bbook chapter\b"),
        ("conference abstract", r"\bconference abstract\b"),
        ("poster", r"\bposter\b"),
        ("editorial", r"\beditorial\b"),
        ("commentary", r"\bcommentary\b"),
        ("case study", r"\bcase study\b"),
        ("case studies", r"\bcase studies\b"),
        ("pilot study", r"\bpilot study\b"),
        ("preliminary study", r"\bpreliminary study\b"),
        ("conceptual", r"\bconceptual\b"),
        ("theoretical", r"\btheoretical\b"),
        ("synthetic study", r"\bsynthetic study\b"),
    ]
)

CONCEPTUAL_PATTERNS = compile_specs(
    [
        ("best practices", r"\bbest practices\b"),
        ("perspective", r"\bperspective\b"),
        ("roadmap", r"\broadmap\b"),
        ("insight", r"\binsights?\b"),
        ("future directions", r"\bfuture directions\b"),
        ("opportunities and challenges", r"\bopportunities and challenges\b"),
        ("challenges and opportunities", r"\bchallenges and opportunities\b"),
        ("framework", r"\bframework\b"),
        ("trends and frontiers", r"\btrends and frontiers\b"),
    ]
)

OFF_TOPIC_PATTERNS = compile_specs(
    [
        ("reservoir", r"\breservoir\b"),
        ("lithology", r"\blitholog\w*\b"),
        ("lithofacies", r"\blithofac\w*\b"),
        ("wellhead", r"\bwellhead\b"),
        ("drilling", r"\bdrilling\b"),
        ("well log", r"\bwell[- ]log\b"),
        ("seismic", r"\bseismic\b"),
        ("fracturing", r"\bfractur\w*\b"),
        ("enhanced oil recovery", r"\benhanced oil recovery\b|\bEOR\b"),
        ("fault diagnosis", r"\bfault diagnosis\b"),
        ("machining", r"\bmachining\b"),
        ("production monitoring", r"\bproduction monitoring\b"),
        ("formation evaluation", r"\bformation evaluation\b"),
        ("well integrity", r"\bwell integrity\b"),
        ("corrosion", r"\bcorrosion\b"),
        ("mud motor", r"\bmud motor\b"),
        ("intrusion detection", r"\bintrusion detection\b"),
        ("anomaly detection", r"\banomaly detection\b"),
        ("tool condition", r"\btool condition\b"),
        ("gas kick", r"\bgas kick\b"),
        ("well control", r"\bwell control\b"),
        ("aerospace", r"\baerospace\b"),
        ("military logistics", r"\bmilitary logistics\b"),
        ("earthquake", r"\bearthquake\b"),
        ("tsunami", r"\btsunami\b"),
        ("landslide", r"\blandslide\b"),
        ("mining", r"\bmining\b"),
    ]
)


@dataclass(frozen=True)
class ArticleMetadata:
    """Representa os metadados minimos usados na triagem."""

    item_id: str
    title: str
    doi: str
    item_type: str
    abstract: str
    manual_tags: str


@dataclass(frozen=True)
class Evidence:
    """Agrupa os sinais coletados nos metadados."""

    sector_hits: dict[str, list[str]]
    scm_hits: dict[str, list[str]]
    ai_hits: dict[str, list[str]]
    support_hits: dict[str, list[str]]
    exclusion_hits: list[str]
    conceptual_hits: list[str]
    off_topic_hits: dict[str, list[str]]
    sector_score: float
    scm_score: float
    ai_score: float
    support_score: float
    off_topic_score: float

    @property
    def has_sector(self) -> bool:
        """Indica se o artigo possui contexto setorial relevante."""

        return any(self.sector_hits.values())

    @property
    def has_direct_sector(self) -> bool:
        """Indica se o setor aparece no titulo ou abstract."""

        return bool(self.sector_hits["title"] or self.sector_hits["abstract"])

    @property
    def has_scm(self) -> bool:
        """Indica se o artigo aborda diretamente SCM/SCRM/logistica/procurement."""

        return any(self.scm_hits.values())

    @property
    def has_direct_scm(self) -> bool:
        """Indica se SCM aparece no titulo ou abstract."""

        return bool(self.scm_hits["title"] or self.scm_hits["abstract"])

    @property
    def has_ai(self) -> bool:
        """Indica se o artigo descreve IA/analytics computacionalmente relevante."""

        return any(self.ai_hits.values())

    @property
    def has_direct_ai(self) -> bool:
        """Indica se IA aparece no titulo ou abstract."""

        return bool(self.ai_hits["title"] or self.ai_hits["abstract"])

    @property
    def has_support_hook(self) -> bool:
        """Indica se existe um gancho analitico, mesmo sem IA explicita."""

        return any(self.support_hits.values())


@dataclass(frozen=True)
class ManualOverride:
    """Representa uma decisao manual para artigos limiares."""

    conservador: str
    moderado: str
    abrangente: str
    note: str

    def decision_for(self, profile: str) -> str:
        """Retorna a decisao do perfil solicitado."""

        return getattr(self, profile)


MANUAL_OVERRIDES: Final[dict[str, ManualOverride]] = {
    "9HL57A4A": ManualOverride("Aprovado", "Aprovado", "Aprovado", "SCM petroquimica com plataforma decisoria integrada e uso de redes neurais/forecasting."),
    "8BBSC9MS": ManualOverride("Aprovado", "Aprovado", "Aprovado", "LLMs aplicados a cost management e supply chain optimization em operacoes de O&G."),
    "VMCW2AU3": ManualOverride("Aprovado", "Aprovado", "Aprovado", "NLP em supply chain de O&G, com foco em compliance e greenwashing."),
    "T8AN86BP": ManualOverride("Aprovado", "Aprovado", "Aprovado", "IA distribuida para processos de transporte de derivados e apoio a decisao."),
    "I8KTHB6A": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Procurement cognitivo e impacto sobre supply chain em O&G com IA explicita."),
    "8UD267LV": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Automacao de technical bid evaluation em oleo com GenAI/LLM e OCR."),
    "LCJD8VP9": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Inventario de pecas e demand forecasting com TFT no setor petroquimico."),
    "T8CGGY4G": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Inventario e previsao com IA para itens ligados a Oil Country Tubular Goods."),
    "NNWFNGC9": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Price forecasting e raw material procurement na industria petroquimica com data science/RL."),
    "7ZXA7CWT": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Predictive analytics para eficiencia de supply chain com dados descentralizados em O&G."),
    "YX7GZHTA": ManualOverride("Aprovado", "Aprovado", "Aprovado", "ML em decision support para modos operacionais de supply vessels offshore."),
    "T49YTRJB": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Planejamento de rotas para armazenamento/transporte de O&G com abordagem computacional."),
    "ZCLGEISX": ManualOverride("Aprovado", "Aprovado", "Aprovado", "Planejamento de abastecimento a postos com modelagem multiagente e roteirizacao."),
    "KN5CQHNH": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Bio-inspired optimization aplicada a supply chain de produtos petroliferos."),
    "WE82JITL": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Procurement em oil marketing com forecast model; IA aparece de forma menos explicita."),
    "EXI7PNPH": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "ML sobre risco entre empresas da petroleum supply chain; relevancia mais financeira que operacional."),
    "QPU9HFN7": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Preco, planejamento e inventario na petroquimica com ANN, mas foco tambem produtivo."),
    "2VRZB86X": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Scheduling de crude oil em refinaria com evolutionary optimization e inventario intermediario."),
    "6W8PCG32": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Risco em projetos de construcao de O&G; tangencia supply/logistica, mas nao e SCM central."),
    "P9NLKAWM": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Warehouse/spare parts em O&G e direto; mesmo sem IA explicita, merece leitura de texto completo."),
    "PCIQFWGI": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Supply chain risk em O&G e direto, relevante para SCRM e apoio a decisao."),
    "FJJTC3RD": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Procurement risk em refinaria e diretamente aderente ao recorte de risco na cadeia."),
    "YY43FKGR": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Critical supply em projetos EPC de O&G, com decisao multicriterio e aderencia parcial."),
    "DFC8PRIQ": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Logistica offshore e supply vessels sao relevantes para a cadeia, mesmo com foco em otimizacao estocastica."),
    "R6RWNFXA": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Fleet sizing de supply vessels offshore tem aderencia logistica direta ao recorte."),
    "JXLRLF83": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Tanker scheduling com inventory cost e confiabilidade e diretamente relevante para logistica energetica."),
    "N675LLWJ": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Resilient supply chain em O&G e diretamente pertinente, embora o componente de IA seja fraco."),
    "ME3S46MC": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Digitalizacao de offshore logistics e pertinente, mas sem IA clara."),
    "7872D7LJ": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Supply chain digital twins citam O&G/petroquimica, mas o recorte e mais amplo e conceitual."),
    "FJCCA7QX": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Decisao em digital supply chains do setor petrolifero e diretamente alinhada ao objetivo da RSL."),
    "BKZRBZRZ": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Inventory-routing e muito proximo do recorte logistico/SCM, ainda que o setor/IA estejam menos explicitos."),
    "44FB2FS3": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Transporte no setor petrolifero e aderente a logistica e otimizacao de cadeia."),
    "3774E5GU": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Selecao de tanker em petroleum logistics e diretamente relevante para decisao logistica."),
    "WA2BQ5D3": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Supply chain de gas natural com metaheuristicas permanece relevante no perfil mais inclusivo."),
    "HQY2NWW6": ManualOverride("Sinalizado", "Aprovado", "Aprovado", "Integrated oil and gas SCM e direto, apesar de combinar temas upstream e EOR."),
    "DMUCTPVW": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Problemas de midstream supply chain e solucoes AI-based justificam leitura completa no perfil amplo."),
    "SX6V7VWW": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "IA e data science em midstream/downstream sao relevantes no perfil abrangente."),
    "RENCPUR3": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Tecnologias disruptivas na petroleum supply chain merecem leitura no perfil mais inclusivo."),
    "7EYCBXKD": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Supply chain finance digital em O&G e tema limiar, mas pertinente no perfil amplo."),
    "57E4Q3XZ": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Blockchain em petroleum supply chain merece leitura no perfil amplo por rastreabilidade/seguranca."),
    "MT3587PH": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Supply chain management com blockchain em O&G e aderente no perfil mais inclusivo."),
    "MIPR67E5": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "LLM ligado a procurement/warehousing/supply chain justifica leitura no perfil amplo."),
    "SS334H5T": ManualOverride("Sinalizado", "Sinalizado", "Aprovado", "Digitalizacao de procurement e bid evaluation em O&G justifica leitura no perfil amplo."),
    "5WNCJCVY": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Trading/traceability no petroleum supply chain e relevante, mas distante do foco SCM/SCRM com IA."),
    "7NV6YR78": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Oil vessel supply chain com neural network, mas validado apenas em dataset sintetico."),
    "7A93NAEV": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Supply chain digital twin e amplo; faltam contexto setorial claro e foco decisorio mais especifico."),
    "A8FUAV7T": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Literature review sobre AI em oil and gas supply chain; excluir por estudo secundario."),
    "UI7JNZNV": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Comprehensive review/best practices; excluir por carater de revisao."),
    "NZPEESZY": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Case study de lead time em O&G services; excluir conforme criterio de estudo de caso."),
    "E5TTRPAA": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Case study de supplier selection na petroquimica; excluir conforme criterio de estudo de caso."),
    "4G8M663G": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Logistics optimization em oil and gas supply chain, mas com case study explicitamente declarado."),
    "VVIC3UEE": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Synthetic study sobre replenishment; excluir por evidencia sintetica/nao elegivel."),
    "UIE3VSDF": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Case of transport logistics in oil company; excluir por estudo de caso."),
    "ZCJL849T": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Vendor selection com case study em petroleum companies; excluir pelo desenho do estudo."),
    "IRK83G3U": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Case study sobre blockchain adoption em O&G; excluir conforme criterio de estudo de caso."),
    "PJUVYGVX": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Foco em theft detection em pipeline, nao em decisao SCM/SCRM."),
    "Q5L2JX9Q": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Automacao de wellpad e controle de ativos, sem foco direto em SCM/SCRM."),
    "MVZ2VK5D": ManualOverride("Reprovado", "Reprovado", "Reprovado", "IA para erros em desenhos de engenharia; tangencial a procurement/SCM."),
    "J54CPWNY": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Digital transformation em accounting de fuel and energy, fora do foco de SCM/SCRM com IA."),
    "W4YZQ78V": ManualOverride("Reprovado", "Reprovado", "Reprovado", "ML para engenharia e construcao de plantas; nao centra decisao SCM/SCRM."),
    "95IDVZH3": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Monitoramento IA para oil industry; falta aderencia direta a SCM/SCRM."),
    "LMUN4GHC": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Digital twin de ciclo de vida do campo; foco operacional, nao supply chain."),
    "4RHI4ZIT": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Supply chain optimization generica, sem contexto setorial direto suficiente."),
    "583FSDBK": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Workshop sobre skills e transicao energetica; nao e estudo primario de SCM/SCRM com IA."),
    "3X2S3UD2": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Cost estimation em desenvolvimento de O&G; relacao com SCM existe, mas permanece indireta."),
    "WL9MJTUQ": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Tecnologias emergentes para CCS; tangencial ao recorte central de SCM/SCRM em O&G."),
    "4DBIIYSF": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Weather classification nao trata de supply chain nem de procurement/logistica decisoria."),
    "F4K77CKP": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Scheduling de shuttle tankers e logistico, mas o contexto setorial/SCM detalhado e limitado."),
    "KDSRYXKN": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Predicao de ondas globais nao tem foco direto em SCM/SCRM."),
    "2WG5LVEY": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Digitizacao de P&ID pode apoiar handover/procurement, mas a conexao com SCM e indireta."),
    "PDCWX4UE": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Modelo de emissoes por simulacao de processo; fora do foco de cadeia de suprimentos."),
    "2UT6YYIZ": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Business decisions em upstream oil gas aparecem de forma muito generica para aprovar leitura completa."),
    "LI32MFI7": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Falha em pipes e manutencao preditiva; nao e SCM/SCRM."),
    "V9HN7GAG": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Fault prediction em regimes tectonicos; sem aderencia a SCM/SCRM."),
    "AX2BSDNH": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Predicao de movimento de navios em ondas; nao e decisao de cadeia de suprimentos."),
    "V3PYKT7T": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Allocation de logistics service providers e pertinente, mas falta contexto setorial/IA mais robusto."),
    "MGYFF69E": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Virtual tour de ativos offshore nao tem foco em SCM/SCRM."),
    "LJRM57MT": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Modelo logistico maritimo para oleo e relevante, mas sem IA explicita e com recorte mais operacional."),
    "KVLMXET6": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Banco de dados de confiabilidade/manutencao de equipamento offshore; relacao com SCM e indireta."),
    "8I65V7K9": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Digital twin em EPC toca material take-off e handover, mas o foco SCM/IA ainda e parcial."),
    "EIKXVHD4": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Business process automation em operacoes de producao; pouca aderencia direta a SCM/SCRM."),
    "S539AM2F": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Big data para price projections no setor; relacao com SCM existe, mas e indireta."),
    "TJ6HPWC2": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Infraestrutura de fibra em ativos offshore; fora do foco de SCM/SCRM."),
    "86UTPF3T": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Estudo de entrevista sobre cybersecurity em ICS; nao e supply chain."),
    "9GQQ2PSV": ManualOverride("Reprovado", "Sinalizado", "Sinalizado", "Freight transport network no contexto de drilling equipment e relevante, mas sem IA clara."),
    "4QSH9BK7": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Inventory-routing generico; aderencia setorial insuficiente no metadata."),
    "KFG4N2IG": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "Gestao de componentes em construcao offshore toca supply, mas nao centra IA/SCM decisoria."),
    "MCH87EQH": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Production back allocation e mais operacional do que supply chain."),
    "5FSKSFSY": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Predicao de preco de resina plastica sem contexto claro de O&G/SCM da RSL."),
    "PP55JMIC": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Iceberg draft assessment nao trata de SCM/SCRM."),
    "AYGWAVS5": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Contamination control em separacao industrial nao e supply chain."),
    "PAJ2CN35": ManualOverride("Reprovado", "Reprovado", "Reprovado", "5G practice em O&G nao apresenta foco direto em SCM/SCRM."),
    "XQKLIBG7": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Membrane replacement scheduling e manutencao operacional, nao supply chain."),
    "8SITWA3S": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Forecast de uso de licencas de software petrolifero nao se alinha ao recorte de SCM/SCRM."),
    "W9LZ8CLP": ManualOverride("Reprovado", "Reprovado", "Reprovado", "Predictive maintenance de annulus wells e tema operacional, nao supply chain."),
    "UD5R39UW": ManualOverride("Reprovado", "Reprovado", "Sinalizado", "AI em EPC e tangencial ao contexto de procurement/SCM; manter apenas no perfil amplo."),
}


def scan_sections(
    sections: dict[str, str],
    patterns: list[tuple[str, re.Pattern[str]]],
) -> tuple[dict[str, list[str]], float]:
    """Varre titulo, abstract e tags com pesos por secao."""

    hits = {name: [] for name in sections}
    score = 0.0
    for section_name, text in sections.items():
        section_hits = [label for label, pattern in patterns if pattern.search(text)]
        hits[section_name] = section_hits
        score += len(section_hits) * SECTION_WEIGHTS[section_name]
    return hits, score


def scan_full_text(
    full_text: str,
    patterns: list[tuple[str, re.Pattern[str]]],
) -> list[str]:
    """Varre o texto combinado para sinais globais."""

    return [label for label, pattern in patterns if pattern.search(full_text)]


def build_evidence(article: ArticleMetadata) -> Evidence:
    """Extrai sinais semanticos a partir dos metadados do artigo."""

    sections = {
        "title": article.title.casefold(),
        "abstract": article.abstract.casefold(),
        "tags": article.manual_tags.casefold(),
    }
    full_text = " ".join(sections.values())
    sector_hits, sector_score = scan_sections(sections, SECTOR_PATTERNS)
    scm_hits, scm_score_strong = scan_sections(sections, SCM_STRONG_PATTERNS)
    support_hits, support_score = scan_sections(sections, SCM_SUPPORT_PATTERNS)
    ai_hits, ai_score_strong = scan_sections(sections, AI_STRONG_PATTERNS)
    ai_support_hits, ai_score_support = scan_sections(sections, AI_SUPPORT_PATTERNS)
    off_topic_hits, off_topic_score = scan_sections(sections, OFF_TOPIC_PATTERNS)
    exclusion_hits = scan_full_text(full_text, EXCLUSION_PATTERNS)
    conceptual_hits = scan_full_text(full_text, CONCEPTUAL_PATTERNS)

    support_hits_merged = {
        name: support_hits[name] + [hit for hit in ai_support_hits[name] if hit not in support_hits[name]]
        for name in sections
    }
    ai_score = ai_score_strong
    scm_score = scm_score_strong
    support_score = support_score + (ai_score_support * 0.75)
    return Evidence(
        sector_hits=sector_hits,
        scm_hits=scm_hits,
        ai_hits=ai_hits,
        support_hits=support_hits_merged,
        exclusion_hits=exclusion_hits,
        conceptual_hits=conceptual_hits,
        off_topic_hits=off_topic_hits,
        sector_score=sector_score,
        scm_score=scm_score,
        ai_score=ai_score,
        support_score=support_score,
        off_topic_score=off_topic_score,
    )


def first_hits(hit_map: dict[str, list[str]], limit: int = 2) -> list[str]:
    """Retorna um pequeno resumo de hits sem duplicatas."""

    ordered: list[str] = []
    for section_name in ("title", "abstract", "tags"):
        for hit in hit_map[section_name]:
            if hit not in ordered:
                ordered.append(hit)
    return ordered[:limit]


def auto_decision(profile: str, evidence: Evidence) -> str:
    """Aplica as regras heuristicas do perfil."""

    if evidence.exclusion_hits:
        return "Reprovado"
    if evidence.off_topic_score >= 6.0 and not evidence.has_direct_scm:
        return "Reprovado"
    if not evidence.has_sector:
        return "Reprovado"
    if profile == "conservador":
        if (
            evidence.has_direct_sector
            and evidence.has_direct_scm
            and evidence.has_direct_ai
            and evidence.off_topic_score < 4.0
            and not evidence.conceptual_hits
        ):
            return "Aprovado"
        if (
            evidence.has_direct_sector
            and evidence.has_direct_scm
            and (evidence.has_ai or evidence.support_score >= 4.0)
            and evidence.off_topic_score < 5.0
        ):
            return "Sinalizado"
        return "Reprovado"
    if profile == "moderado":
        if (
            evidence.has_direct_sector
            and evidence.has_direct_scm
            and (evidence.has_ai or evidence.support_score >= 4.0)
            and evidence.off_topic_score < 5.0
        ):
            return "Aprovado"
        if (
            evidence.has_direct_sector
            and evidence.has_scm
            and (evidence.has_ai or evidence.support_score >= 2.0)
            and evidence.off_topic_score < 6.0
        ):
            return "Sinalizado"
        return "Reprovado"
    if (
        evidence.has_direct_sector
        and evidence.has_direct_scm
        and (evidence.has_ai or evidence.support_score >= 2.0)
        and evidence.off_topic_score < 6.0
    ):
        return "Aprovado"
    if (
        evidence.has_sector
        and evidence.has_scm
        and (evidence.has_ai or evidence.support_score >= 1.5)
        and evidence.off_topic_score < 7.0
    ):
        return "Sinalizado"
    return "Reprovado"


def summarize_hits(hit_map: dict[str, list[str]]) -> str:
    """Resume os principais termos acionados."""

    values = first_hits(hit_map, limit=2)
    return ", ".join(values) if values else "sem termo claro"


def build_motivation(profile: str, decision: str, evidence: Evidence) -> str:
    """Gera a motivacao textual usada no CSV."""

    if evidence.exclusion_hits:
        reasons = ", ".join(evidence.exclusion_hits[:2])
        return f"Excluido por tipo de estudo/metodo nao elegivel no metadata: {reasons}."
    if decision == "Aprovado":
        sector = summarize_hits(evidence.sector_hits)
        scm = summarize_hits(evidence.scm_hits)
        ai = summarize_hits(evidence.ai_hits)
        return f"Aderencia direta ao recorte: setor {sector}; tema {scm}; tecnologia {ai}."
    if decision == "Sinalizado":
        if evidence.has_sector and evidence.has_scm and not evidence.has_ai:
            return (
                "Tema setorial e de SCM/SCRM parece direto, mas IA/analytics nao esta suficientemente "
                f"explicita no metadata para o perfil {profile}."
            )
        if evidence.has_sector and evidence.has_ai and not evidence.has_scm:
            return (
                "Ha IA em contexto de O&G/petroquimica, mas a conexao com SCM/SCRM permanece indireta "
                f"no metadata para o perfil {profile}."
            )
        if evidence.has_sector and evidence.has_scm:
            return (
                "Ha proximidade com o recorte da RSL, mas permanece ambiguidade metodologica/setorial "
                f"e o perfil {profile} pede revisao humana."
            )
        return f"Artigo limiar para o perfil {profile}; revisar texto completo antes de excluir."
    if evidence.off_topic_score >= 4.0 and not evidence.has_direct_scm:
        return "Foco principal em operacao/engenharia do ativo, nao em decisao SCM/SCRM."
    if not evidence.has_sector:
        return "Metadata nao situa o estudo de forma clara em oleo/gas ou petroquimica."
    if not evidence.has_scm:
        return "Nao apresenta foco direto em supply chain, procurement, logistica ou risco na cadeia."
    if not evidence.has_ai and evidence.support_score < 2.0:
        return "Tema setorial ate aparece, mas o uso de IA/analytics para decisao nao esta claro."
    return "Relevancia direta insuficiente para seguir a leitura de texto completo neste perfil."


def decide_article(profile: str, article: ArticleMetadata, evidence: Evidence) -> tuple[str, str]:
    """Decide a triagem de um artigo para um perfil especifico."""

    override = MANUAL_OVERRIDES.get(article.item_id)
    if override is not None:
        return override.decision_for(profile), override.note
    decision = auto_decision(profile, evidence)
    if decision == "Aprovado" and evidence.conceptual_hits and not evidence.has_direct_ai:
        decision = "Sinalizado"
    return decision, build_motivation(profile, decision, evidence)


def load_articles(csv_path: Path) -> list[ArticleMetadata]:
    """Carrega o corpus exportado do Zotero."""

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            ArticleMetadata(
                item_id=row.get("Key", "").strip(),
                title=row.get("Title", "").strip(),
                doi=row.get("DOI", "").strip(),
                item_type=row.get("Item Type", "").strip(),
                abstract=row.get("Abstract Note", "").strip(),
                manual_tags=row.get("Manual Tags", "").strip(),
            )
            for row in reader
        ]


def export_profile(
    output_path: Path,
    profile: str,
    articles: list[ArticleMetadata],
) -> dict[str, int]:
    """Exporta um CSV de triagem para um perfil e retorna o resumo de contagens."""

    counts = {"Aprovado": 0, "Sinalizado": 0, "Reprovado": 0}
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "Titulo", "DOI", "decisao", "motivacao"])
        for article in articles:
            evidence = build_evidence(article)
            decision, motivation = decide_article(profile, article, evidence)
            counts[decision] += 1
            writer.writerow([article.item_id, article.title, article.doi, decision, motivation])
    return counts


def parse_args() -> argparse.Namespace:
    """Le os argumentos da linha de comando."""

    parser = argparse.ArgumentParser(description="Triagem inicial de metadados para RSL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("Final_Corpus.csv"),
        help="Caminho para o CSV exportado do Zotero.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Diretorio onde os CSVs de saida serao gerados.",
    )
    return parser.parse_args()


def main() -> None:
    """Executa a triagem para os tres perfis."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    articles = load_articles(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Artigos carregados: %s", len(articles))
    for profile in PROFILES:
        output_path = args.output_dir / f"triagem_rsl_{profile}.csv"
        counts = export_profile(output_path, profile, articles)
        LOGGER.info("%s -> %s", output_path.name, counts)


if __name__ == "__main__":
    main()
