"""
Triagem automatizada de artigos para RSL.

Pesquisa: IA aplicada a SCM/SCRM na industria de Oleo & Gas.
Pergunta CIMO: No contexto da gestao de projetos na industria de oleo & gas,
como ferramentas de IA que integram dados dispersos da cadeia de suprimentos
auxiliam a tomada de decisoes na gestao da cadeia de suprimentos (SCM) e/ou
gestao de riscos na cadeia de suprimentos (SCRM)?

Gera 3 perfis: conservador, moderado, abrangente.
"""

import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. KEYWORDS POR DIMENSAO
# ---------------------------------------------------------------------------

# Dimensao 1: Dominio O&G
OG_KEYWORDS = [
    # Core O&G
    r"\boil\s*(?:and|&)\s*gas\b", r"\bpetroleum\b", r"\bpetrochemical\b",
    r"\bhydrocarbon\b", r"\bupstream\b", r"\bdownstream\b", r"\bmidstream\b",
    r"\boffshore\b", r"\bonshore\b", r"\bsubsea\b", r"\brefinery\b",
    r"\brefining\b", r"\bdrilling\b", r"\bwell\s*head\b", r"\bpipeline\b",
    r"\blng\b", r"\blpg\b", r"\bfpso\b", r"\brig\b",
    r"\bcrude\s*oil\b", r"\bnatural\s*gas\b", r"\bshale\b",
    r"\breservoir\b", r"\bwellbore\b", r"\bflowline\b",
    r"\bgas\s*plant\b", r"\bgas\s*processing\b", r"\boilfield\b",
    r"\boil\s*field\b", r"\bgas\s*field\b", r"\benergy\s*sector\b",
    r"\benergy\s*industry\b", r"\bfossil\s*fuel\b",
    r"\bexploration\s*and\s*production\b", r"\be&p\b", r"\bepc\b",
    r"\bnaphtha\b", r"\bblowout\b", r"\bcompletion\b",
    r"\bproduction\s*logging\b", r"\bwell\s*log\b",
    # Broader energy (weighted lower via scoring)
    r"\benergy\b", r"\bpower\s*plant\b", r"\bpower\s*generation\b",
]

# Dimensao 2: IA / ML
AI_KEYWORDS = [
    r"\bartificial\s*intelligence\b", r"\bmachine\s*learning\b",
    r"\bdeep\s*learning\b", r"\bneural\s*network\b", r"\breinforcement\s*learning\b",
    r"\bnatural\s*language\s*processing\b", r"\bnlp\b",
    r"\bcomputer\s*vision\b", r"\bpredictive\s*model\b",
    r"\bpredictive\s*analytics\b", r"\bpredictive\s*analysis\b",
    r"\bclassification\s*algorithm\b", r"\bclustering\b",
    r"\brandom\s*forest\b", r"\bdecision\s*tree\b", r"\bsvm\b",
    r"\bsupport\s*vector\b", r"\bgradient\s*boosting\b", r"\bxgboost\b",
    r"\blstm\b", r"\bcnn\b", r"\brnn\b", r"\btransformer\b",
    r"\bbert\b", r"\bgpt\b", r"\bllm\b", r"\blarge\s*language\s*model\b",
    r"\bgenerative\s*ai\b", r"\bgen\s*ai\b",
    r"\bbayesian\b", r"\bfuzzy\s*logic\b", r"\bgenetic\s*algorithm\b",
    r"\bevolutionary\s*algorithm\b", r"\bant\s*colony\b",
    r"\bparticle\s*swarm\b", r"\boptimi[sz]ation\s*algorithm\b",
    r"\bmetaheuristic\b", r"\bswarm\s*(?:intelligence|optimi)\b",
    r"\bheuristic\s*algorithm\b", r"\bhybrid\s*algorithm\b",
    r"\bdata\s*mining\b", r"\bdata[\s-]*driven\b",
    r"\bdigital\s*twin\b", r"\binternet\s*of\s*things\b", r"\biot\b",
    r"\bbig\s*data\b", r"\bcloud\s*computing\b",
    r"\bautomation\b", r"\bintelligent\s*system\b",
    r"\bknowledge\s*graph\b", r"\bontology\b",
    r"\banomal(?:y|ies)\s*detection\b", r"\bprediction\b",
    r"\bforecasting\b", r"\bregression\b",
    r"\b(?:ai|ml)\b",
]

# Dimensao 3: SCM / SCRM / Logistica / Procurement
# Dividido em CORE (alta confianca - diretamente sobre cadeia de suprimentos)
# e CONTEXTUAL (baixa confianca - podem aparecer fora de contexto SCM)
SCM_CORE_KEYWORDS = [
    r"\bsupply\s*chain\b", r"\bscm\b", r"\bscrm\b",
    r"\bprocurement\b", r"\bsourcing\b", r"\bvendor\b",
    r"\bsupplier\b", r"\blogistics\b", r"\bwarehou\w*\b", r"\binventory\b",
    r"\blead\s*time\b", r"\bfreight\b", r"\bshipment\b",
    r"\bdemand\s*forecast\b", r"\bdemand\s*planning\b",
    r"\bsafety\s*stock\b", r"\bbullwhip\b",
    r"\bsupply\s*risk\b", r"\bsupply\s*disruption\b",
    r"\bsupply\s*network\b", r"\btransportation\b",
    r"\bmaterial\s*management\b", r"\bvalue\s*chain\b",
    r"\boperations\s*management\b",
    r"\bcost\s*overrun\b", r"\bproject\s*delay\b",
    r"\bproject\s*management\b", r"\bproject\s*planning\b",
    r"\bresource\s*allocation\b", r"\bcapacity\s*planning\b",
]

SCM_CONTEXTUAL_KEYWORDS = [
    r"\brisk\s*management\b", r"\brisk\s*mitigation\b",
    r"\brisk\s*assessment\b", r"\brisk\s*analysis\b",
    r"\bscheduling\b", r"\bplanning\b",
    r"\bmanufacturing\b", r"\bfabrication\b", r"\binspection\b",
    r"\bquality\s*control\b", r"\bquality\s*assurance\b",
    r"\bcontract\b", r"\bdelivery\b", r"\bdistribution\b",
    r"\bdelay\b", r"\bbudget\b", r"\bstakeholder\b",
]

# Combinacao completa para contagem total
SCM_KEYWORDS = SCM_CORE_KEYWORDS + SCM_CONTEXTUAL_KEYWORDS

# Dimensao 4: Tomada de decisao
DECISION_KEYWORDS = [
    r"\bdecision[\s-]*mak\w*\b", r"\bdecision\s*support\b",
    r"\bdss\b", r"\boptimiz\w*\b", r"\brecommend\w*\b",
    r"\bprescriptive\b", r"\bperformance\s*evaluat\b",
    r"\bbenchmark\b", r"\bkpi\b", r"\bmetric\b",
    r"\baction\w*\s*insight\b", r"\bstrategic\b",
    r"\boperational\s*excellen\b", r"\befficiency\b",
    r"\bcost\s*reduc\b", r"\bcost\s*sav\b",
    r"\bproductivity\b", r"\bperformance\b",
    r"\breal[\s-]*time\b", r"\bpredictive\s*maintenance\b",
    r"\bcondition\s*monitoring\b", r"\bprognostic\b",
    r"\bdiagnostic\b", r"\bearly\s*warning\b",
    r"\bsimulation\b", r"\bscenario\b",
]

# ---------------------------------------------------------------------------
# 2. DETECCAO DE TIPOS EXCLUDENTES (pelo titulo/abstract)
# ---------------------------------------------------------------------------

EXCLUDED_TYPE_PATTERNS = [
    (r"\b(?:systematic|literature|scoping)\s*review\b", "systematic/literature review"),
    (r"\bmeta[\s-]*analy\w*\b", "meta-analysis"),
    (r"\bsurvey\s*(?:paper|of|on)\b", "survey paper"),
    (r"\b(?:a|comprehensive)\s*survey\b", "survey paper"),
    (r"\btutorial\b", "tutorial"),
    (r"\bbook\s*chapter\b", "book chapter"),
    (r"\bconference\s*abstract\b", "conference abstract"),
    (r"\bposter\s*(?:session|presentation)\b", "poster"),
    (r"\beditorial\b", "editorial"),
    (r"\bcommentary\b", "commentary"),
    (r"\b(?:a\s+)?case\s*stud(?:y|ies)\b", "case study"),
    (r"\bpilot\s*stud(?:y|ies)\b", "pilot study"),
    (r"\bpreliminary\s*stud(?:y|ies)\b", "preliminary study"),
    (r"\bconceptual\s*(?:framework|model|paper|study)\b", "conceptual paper"),
    (r"\btheoretical\s*(?:framework|model|paper|study|analysis)\b", "theoretical paper"),
    (r"\bstate[\s-]*of[\s-]*the[\s-]*art\b", "survey/review"),
    (r"\bbibliometric\b", "bibliometric review"),
    (r"\bovervi?ew\s*of\b", "overview/survey"),
]


def compile_patterns(keywords):
    return [re.compile(k, re.IGNORECASE) for k in keywords]


OG_RE = compile_patterns(OG_KEYWORDS)
AI_RE = compile_patterns(AI_KEYWORDS)
SCM_RE = compile_patterns(SCM_KEYWORDS)
SCM_CORE_RE = compile_patterns(SCM_CORE_KEYWORDS)
SCM_CTX_RE = compile_patterns(SCM_CONTEXTUAL_KEYWORDS)
DEC_RE = compile_patterns(DECISION_KEYWORDS)
EXCL_RE = [(re.compile(p, re.IGNORECASE), label) for p, label in EXCLUDED_TYPE_PATTERNS]


def count_matches(text, patterns):
    """Conta quantos patterns distintos dao match no texto."""
    return sum(1 for p in patterns if p.search(text))


def detect_excluded_type(title, abstract):
    """Detecta se artigo e de tipo excluido. Retorna (bool, motivo)."""
    # Prioriza titulo (mais confiavel)
    for pat, label in EXCL_RE:
        if pat.search(title):
            return True, label
    # Verifica abstract somente para padroes fortes
    strong = [
        r"\bthis\s+(?:systematic|literature|scoping)\s*review\b",
        r"\bthis\s+survey\b",
        r"\bthis\s+meta[\s-]*analy\w*\b",
        r"\bwe\s+(?:conduct|present|perform)\w*\s+a\s+(?:systematic|literature)\s*review\b",
        r"\bbibliometric\s+analysis\b",
        r"\bthis\s+paper\s+(?:reviews|surveys)\b",
    ]
    for p in strong:
        if re.search(p, abstract, re.IGNORECASE):
            return True, "detected in abstract"
    return False, ""


# ---------------------------------------------------------------------------
# 3. SCORING E TRIAGEM
# ---------------------------------------------------------------------------

def score_article(title, abstract, tags):
    """Retorna scores por dimensao e score total.

    Diferencia SCM core (supply chain, logistics, procurement...) de
    SCM contextual (planning, scheduling, manufacturing...) para evitar
    falsos positivos em artigos de engenharia/geologia.
    """
    text = f"{title} {abstract} {tags}".lower()
    title_low = title.lower()

    og = count_matches(text, OG_RE)
    ai = count_matches(text, AI_RE)
    scm = count_matches(text, SCM_RE)
    scm_core = count_matches(text, SCM_CORE_RE)
    scm_ctx = count_matches(text, SCM_CTX_RE)
    dec = count_matches(text, DEC_RE)

    # Bonus: titulo com keywords ganha peso extra
    og_title = count_matches(title_low, OG_RE)
    ai_title = count_matches(title_low, AI_RE)
    scm_title = count_matches(title_low, SCM_RE)
    scm_core_title = count_matches(title_low, SCM_CORE_RE)

    # Score ponderado — SCM core vale muito mais que contextual
    score = (
        min(og, 5) * 2.0 +            # O&G: ate 10 pts
        og_title * 1.5 +               # bonus titulo O&G
        min(ai, 6) * 1.5 +            # AI: ate 9 pts
        ai_title * 1.0 +               # bonus titulo AI
        min(scm_core, 5) * 3.0 +      # SCM core: ate 15 pts
        min(scm_ctx, 4) * 1.0 +       # SCM contextual: ate 4 pts
        scm_core_title * 3.0 +         # bonus titulo SCM core (forte)
        scm_title * 1.0 +              # bonus titulo SCM geral
        min(dec, 4) * 1.0 +           # Decisao: ate 4 pts
        0
    )

    return {
        'og': og, 'ai': ai, 'scm': scm,
        'scm_core': scm_core, 'scm_ctx': scm_ctx,
        'dec': dec,
        'og_t': og_title, 'ai_t': ai_title,
        'scm_t': scm_title, 'scm_core_t': scm_core_title,
        'score': round(score, 1),
    }


def classify_article(scores, is_excluded, excl_reason, title, abstract):
    """
    Retorna (decisao, motivacao) para cada perfil.
    Decisoes: Aprovado, Reprovado, Sinalizado

    Logica central: o corpus ja foi pre-filtrado por O&G + IA nos search strings,
    entao a dimensao SCM/SCRM e o diferenciador critico. Artigos sem qualquer
    sinal de cadeia de suprimentos/gestao de riscos/logistica sao provavelmente
    sobre geologia, reservatorio, equipamentos ou processos quimicos — fora do
    escopo da RSL.
    """
    og = scores['og']
    ai = scores['ai']
    scm = scores['scm']
    dec = scores['dec']
    total = scores['score']

    results = {}

    for profile in ('conservador', 'moderado', 'abrangente'):
        decision = None
        reason_parts = []

        # ---- Exclusao por tipo de artigo ----
        if is_excluded:
            if profile == 'abrangente':
                decision = "Sinalizado"
                reason_parts.append(f"Tipo possivelmente excluido ({excl_reason}); verificar se contem dados primarios")
            else:
                decision = "Reprovado"
                reason_parts.append(f"Tipo excluido: {excl_reason}")
                results[profile] = (decision, "; ".join(reason_parts))
                continue

        # ---- Artigo sem abstract ----
        if not abstract.strip():
            decision = "Sinalizado"
            reason_parts.append("Sem abstract disponivel; revisao humana necessaria")
            results[profile] = (decision, "; ".join(reason_parts))
            continue

        # ---- Verificacao de dimensoes ----
        scm_core = scores['scm_core']
        scm_ctx = scores['scm_ctx']

        has_og = og >= 1
        has_ai = ai >= 1
        # SCM: exige pelo menos 1 keyword CORE para contar como presente
        has_scm = scm_core >= 1
        has_dec = dec >= 1

        # SCM forte = 2+ core matches (nao apenas mencao isolada)
        scm_strong = scm_core >= 2
        # SCM no titulo = sinal muito forte
        scm_in_title = scores['scm_core_t'] >= 1

        dims_present = sum([has_og, has_ai, has_scm])

        if profile == 'conservador':
            # Exige: SCM core forte + O&G + IA, score alto
            if has_scm and scm_strong and has_og and has_ai and total >= 15:
                decision = "Aprovado"
                reason_parts.append(f"O&G({og}) + IA({ai}) + SCM_core({scm_core}) + Score({total})")
            elif has_scm and scm_in_title and has_og and has_ai and total >= 12:
                decision = "Aprovado"
                reason_parts.append(f"SCM no titulo + O&G({og}) + IA({ai}) + Score({total})")
            elif dims_present == 3 and total >= 12:
                decision = "Sinalizado"
                reason_parts.append(f"3 dimensoes presentes; SCM_core={scm_core}, score={total}; verificar profundidade SCM")
            elif has_scm and scm_strong and dims_present == 2 and total >= 18:
                decision = "Sinalizado"
                missing = []
                if not has_og: missing.append("O&G")
                if not has_ai: missing.append("IA")
                reason_parts.append(f"SCM core forte({scm_core}) + score alto({total}); falta: {', '.join(missing)}")
            elif dims_present == 2 and has_scm and total >= 15:
                decision = "Sinalizado"
                missing = []
                if not has_og: missing.append("O&G")
                if not has_ai: missing.append("IA")
                reason_parts.append(f"SCM_core({scm_core}) + score({total}); falta: {', '.join(missing)}")
            else:
                decision = "Reprovado"
                if not has_scm:
                    if scm_ctx > 0:
                        reason_parts.append(f"Apenas SCM contextual({scm_ctx}), sem core; O&G={og}, IA={ai}")
                    else:
                        reason_parts.append(f"Sem sinal de SCM/SCRM/logistica; O&G={og}, IA={ai}")
                elif dims_present <= 1:
                    present = []
                    if has_og: present.append("O&G")
                    if has_ai: present.append("IA")
                    if has_scm: present.append("SCM")
                    reason_parts.append(f"Apenas dimensao: {', '.join(present)}; insuficiente")
                else:
                    reason_parts.append(f"Score insuficiente ({total}); O&G={og}, IA={ai}, SCM_core={scm_core}")

        elif profile == 'moderado':
            # Exige: SCM core presente + pelo menos 1 outra dimensao
            if dims_present == 3 and total >= 10:
                decision = "Aprovado"
                reason_parts.append(f"O&G({og}) + IA({ai}) + SCM_core({scm_core}) + Score({total})")
            elif dims_present == 3 and total < 10:
                decision = "Sinalizado"
                reason_parts.append(f"3 dimensoes mas score baixo ({total}); SCM_core={scm_core}")
            elif has_scm and dims_present == 2 and total >= 8:
                missing = []
                if not has_og: missing.append("O&G")
                if not has_ai: missing.append("IA")
                decision = "Aprovado"
                reason_parts.append(f"SCM_core({scm_core}) + dimensao + score({total}); falta: {', '.join(missing)}")
            elif has_scm and dims_present == 2 and total >= 5:
                decision = "Sinalizado"
                missing = []
                if not has_og: missing.append("O&G")
                if not has_ai: missing.append("IA")
                reason_parts.append(f"SCM_core({scm_core}) + score moderado ({total}); falta: {', '.join(missing)}")
            elif not has_scm and scm_ctx >= 2 and dims_present >= 2 and total >= 12:
                # O&G + IA com contextuais SCM — pode ter relevancia implicita
                decision = "Sinalizado"
                reason_parts.append(f"O&G({og}) + IA({ai}) + SCM contextual({scm_ctx}) sem core; verificar manualmente")
            elif has_scm and dims_present == 1 and total >= 12:
                decision = "Sinalizado"
                reason_parts.append(f"Apenas SCM_core({scm_core}) + score({total}); falta contexto O&G/IA")
            else:
                decision = "Reprovado"
                if not has_scm:
                    if scm_ctx > 0:
                        reason_parts.append(f"Apenas SCM contextual({scm_ctx}), sem core; O&G={og}, IA={ai}")
                    else:
                        reason_parts.append(f"Sem sinal de SCM/SCRM/logistica; O&G={og}, IA={ai}, score={total}")
                elif dims_present <= 1:
                    reason_parts.append(f"Dimensoes insuficientes ({dims_present}/3); SCM_core={scm_core}, score={total}")
                else:
                    reason_parts.append(f"Score insuficiente ({total}); O&G={og}, IA={ai}, SCM_core={scm_core}")

        else:  # abrangente
            # Inclui com sinais mais fracos, mas SCM core continua prioritario
            if dims_present == 3:
                decision = "Aprovado"
                reason_parts.append(f"O&G({og}) + IA({ai}) + SCM_core({scm_core}) + Score({total})")
            elif has_scm and dims_present == 2:
                decision = "Aprovado"
                missing = []
                if not has_og: missing.append("O&G")
                if not has_ai: missing.append("IA")
                reason_parts.append(f"SCM_core({scm_core}) + dimensao; falta: {', '.join(missing)}; score={total}")
            elif not has_scm and scm_ctx >= 2 and dims_present == 2 and total >= 10:
                # O&G + IA com contextuais SCM
                decision = "Sinalizado"
                reason_parts.append(f"O&G({og}) + IA({ai}) + SCM contextual({scm_ctx}); pode ter relevancia indireta")
            elif not has_scm and dims_present == 2 and total >= 12:
                decision = "Sinalizado"
                reason_parts.append(f"O&G({og}) + IA({ai}) sem SCM; score alto ({total}); verificar")
            elif has_scm and dims_present == 1 and total >= 5:
                decision = "Sinalizado"
                reason_parts.append(f"Apenas SCM_core({scm_core}) + score({total}); verificar contexto")
            elif not has_scm and scm_ctx >= 3 and total >= 10:
                decision = "Sinalizado"
                reason_parts.append(f"SCM contextual forte({scm_ctx}) sem core; score({total}); pode ser relevante")
            else:
                decision = "Reprovado"
                if not has_scm and scm_ctx == 0:
                    reason_parts.append(f"Sem qualquer sinal SCM; O&G={og}, IA={ai}, score={total}")
                elif not has_scm:
                    reason_parts.append(f"Apenas SCM contextual({scm_ctx}), sem core; O&G={og}, IA={ai}")
                else:
                    reason_parts.append(f"Relevancia insuficiente; O&G={og}, IA={ai}, SCM_core={scm_core}")

        results[profile] = (decision, "; ".join(reason_parts))

    return results


# ---------------------------------------------------------------------------
# 4. PROCESSAMENTO PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    csv_path = Path(__file__).parent / "Final_Corpus.csv"
    out_dir = Path(__file__).parent

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"Processando {len(articles)} artigos...")

    all_results = []

    for i, row in enumerate(articles):
        key = row.get('Key', f'ART_{i+1}')
        title = row.get('Title', '')
        doi = row.get('DOI', '')
        abstract = row.get('Abstract Note', '')
        tags = row.get('Manual Tags', '') + ' ' + row.get('Automatic Tags', '')

        # Detecta tipo excluido
        is_excluded, excl_reason = detect_excluded_type(title, abstract)

        # Calcula scores
        scores = score_article(title, abstract, tags)

        # Classifica nos 3 perfis
        classifications = classify_article(scores, is_excluded, excl_reason, title, abstract)

        all_results.append({
            'key': key,
            'title': title,
            'doi': doi,
            'scores': scores,
            'is_excluded': is_excluded,
            'excl_reason': excl_reason,
            'classifications': classifications,
        })

    # Gera CSVs por perfil
    for profile in ('conservador', 'moderado', 'abrangente'):
        out_path = out_dir / f"triage_{profile}.csv"

        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Titulo', 'DOI', 'Decisao', 'Motivacao'])

            for r in all_results:
                decision, reason = r['classifications'][profile]
                writer.writerow([
                    r['key'],
                    r['title'],
                    r['doi'],
                    decision,
                    reason,
                ])

        # Contabiliza
        counts = {'Aprovado': 0, 'Reprovado': 0, 'Sinalizado': 0}
        for r in all_results:
            d, _ = r['classifications'][profile]
            counts[d] = counts.get(d, 0) + 1

        print(f"\n=== Perfil {profile.upper()} ===")
        print(f"  Aprovados:   {counts['Aprovado']:>4} ({100*counts['Aprovado']/len(all_results):.1f}%)")
        print(f"  Sinalizados: {counts['Sinalizado']:>4} ({100*counts['Sinalizado']/len(all_results):.1f}%)")
        print(f"  Reprovados:  {counts['Reprovado']:>4} ({100*counts['Reprovado']/len(all_results):.1f}%)")
        print(f"  Arquivo: {out_path.name}")

    # Artigos excluidos por tipo
    excluded = [r for r in all_results if r['is_excluded']]
    print(f"\n=== Artigos com tipo excluido (review/survey/etc): {len(excluded)} ===")
    type_counts = {}
    for r in excluded:
        t = r['excl_reason']
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Top 20 aprovados no perfil conservador (por score)
    approved_cons = [(r['scores']['score'], r['title'][:80], r['key'])
                     for r in all_results
                     if r['classifications']['conservador'][0] == 'Aprovado']
    approved_cons.sort(reverse=True)
    print(f"\n=== Top 20 Aprovados (Conservador) por score ===")
    for score, title, key in approved_cons[:20]:
        print(f"  [{score:5.1f}] {title}")

    print(f"\nTriagem concluida! 3 CSVs gerados em: {out_dir}")


if __name__ == '__main__':
    main()
