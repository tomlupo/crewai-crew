"""
Dedicated verifier agent factory.

Antfarm pattern: the Verifier agent is a separate agent with a single
responsibility — check work against acceptance criteria. It runs in its
own fresh session and has no knowledge of how the work was produced.
"""

from crewai import Agent


def create_verifier(
    llm: str | None = None,
    domain_context: str = "",
) -> Agent:
    """
    Create a verifier agent.

    The verifier's only job is to check other agents' output for
    completeness, accuracy, and format compliance. It should be
    a different model or at least a different agent instance from
    the one that produced the work.

    Args:
        llm: Model to use. Recommend a cheaper model for cost efficiency
             (e.g., claude-haiku-4-5-20251001 for verification of
             claude-sonnet-4-5-20250929 work).
        domain_context: Additional context about what correct output
                       looks like in this domain.

    Returns:
        CrewAI Agent configured as a verifier.
    """
    backstory = (
        "You are a meticulous quality assurance reviewer. Your only job is to "
        "verify that work output meets the specified requirements. You check for:\n"
        "- Completeness: all required fields and sections present\n"
        "- Accuracy: facts, numbers, and calculations are correct\n"
        "- Format: output follows the required KEY: value structure\n"
        "- Logic: reasoning is sound and conclusions follow from evidence\n\n"
        "You are strict but fair. You approve work that meets requirements and "
        "reject work that doesn't, with specific feedback on what needs fixing.\n"
        "You NEVER produce the work yourself — only verify it."
    )

    if domain_context:
        backstory += f"\n\nDomain context:\n{domain_context}"

    agent_config = {
        "role": "Quality Verifier",
        "goal": "Verify output meets all requirements. Approve good work, reject bad work with specific feedback.",
        "backstory": backstory,
        "verbose": False,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)


def create_domain_verifier(
    domain: str,
    checks: list[str],
    llm: str | None = None,
) -> Agent:
    """
    Create a domain-specific verifier with explicit check criteria.

    Example for quant finance:
        verifier = create_domain_verifier(
            domain="quantitative fund analysis",
            checks=[
                "Sharpe ratios are between -2 and 5 (realistic range)",
                "AUM values are in correct currency units (PLN or EUR)",
                "Fund names match known Polish fund names",
                "Performance data has correct date ranges",
                "No duplicate funds in the output",
            ],
        )
    """
    checks_text = "\n".join(f"- {c}" for c in checks)
    domain_context = (
        f"You are verifying output in the domain of {domain}.\n\n"
        f"Specific checks to perform:\n{checks_text}\n\n"
        f"If ANY check fails, reject with STATUS: rejected and explain which "
        f"check failed and why."
    )

    return create_verifier(llm=llm, domain_context=domain_context)
