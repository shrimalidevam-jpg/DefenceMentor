"""Add the NDA Mathematics chapters and syllabus topics."""

from datetime import datetime, timezone
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op


revision = "20261007_0026"
down_revision = "20261007_0025"
branch_labels = None
depends_on = None

NAMESPACE = UUID("2f2164d4-84c1-4e75-9496-f242d1f4d782")

SYLLABUS = (
    (
        "Algebra",
        "Sets, number systems, progressions, equations, counting, the binomial theorem and logarithms.",
        (
            ("Sets, Relations and Functions", "Set operations, Venn diagrams, De Morgan laws, Cartesian products, relations and equivalence relations.", (
                ("Set operations and Venn diagrams", "Represent sets and perform union, intersection, difference and complement operations using Venn diagrams."),
                ("De Morgan laws", "Apply De Morgan laws to complements of unions and intersections."),
                ("Cartesian products", "Form Cartesian products of sets and represent ordered pairs."),
                ("Relations and equivalence relations", "Represent relations and check the reflexive, symmetric and transitive properties of equivalence relations."),
            )),
            ("Number Systems", "Real numbers on a number line, complex numbers and the binary number system.", (
                ("Real numbers on a line", "Represent and compare real numbers on the number line."),
                ("Complex numbers", "Use the basic properties of complex numbers, including modulus and argument."),
                ("Cube roots of unity", "Use the properties and basic identities of the cube roots of unity."),
                ("Binary numbers", "Convert numbers between decimal and binary systems."),
            )),
            ("Sequences and Series", "Arithmetic, geometric and harmonic progressions.", (
                ("Arithmetic progression", "Identify an arithmetic progression and use its common difference and standard term and sum relations."),
                ("Geometric progression", "Identify a geometric progression and use its common ratio and standard term and sum relations."),
                ("Harmonic progression", "Recognise harmonic progressions and relate their terms to an arithmetic progression."),
            )),
            ("Equations and Inequalities", "Quadratic equations with real coefficients and graphical solutions of linear inequalities in two variables.", (
                ("Quadratic equations", "Solve quadratic equations with real coefficients and interpret their roots."),
                ("Linear inequalities in two variables", "Represent and solve linear inequalities in two variables using graphs."),
            )),
            ("Permutations, Combinations and Binomial Theorem", "Permutation and combination, and the binomial theorem with applications.", (
                ("Permutations", "Count arrangements when order matters."),
                ("Combinations", "Count selections when order does not matter."),
                ("Binomial theorem", "Expand binomial expressions and apply the binomial theorem to problems."),
            )),
            ("Logarithms", "Logarithms and their applications.", (
                ("Laws of logarithms", "Use logarithm laws to simplify and evaluate logarithmic expressions."),
                ("Applications of logarithms", "Apply logarithms to solve problems involving powers and exponential relationships."),
            )),
        ),
    ),
    (
        "Matrices and Determinants",
        "Matrix types and operations, determinants, inverses, and systems of linear equations.",
        (
            ("Matrices and Operations", "Types of matrices and operations on matrices.", (
                ("Types of matrices", "Identify common matrix types, including square, diagonal, scalar, identity and zero matrices."),
                ("Matrix operations", "Add and multiply matrices and use scalar multiplication when dimensions permit."),
            )),
            ("Determinants", "Determinants and their basic properties.", (
                ("Determinants", "Evaluate determinants of square matrices."),
                ("Properties of determinants", "Use basic determinant properties to simplify calculations."),
            )),
            ("Adjoint and Inverse of a Matrix", "Adjoint and inverse of a square matrix.", (
                ("Adjoint of a square matrix", "Find the adjoint of a square matrix."),
                ("Inverse of a square matrix", "Determine whether a square matrix is invertible and find its inverse."),
            )),
            ("Systems of Linear Equations", "Solve systems in two or three unknowns using Cramer's rule and the matrix method.", (
                ("Cramer's rule", "Solve systems of linear equations in two or three unknowns using determinants."),
                ("Matrix method", "Represent and solve systems of linear equations using matrix inverses."),
            )),
        ),
    ),
    (
        "Trigonometry",
        "Angles and trigonometric ratios, identities, inverse functions, and applications.",
        (
            ("Angles and Trigonometric Ratios", "Angle measures in degrees and radians, and trigonometric ratios.", (
                ("Degree and radian measures", "Convert angle measures between degrees and radians."),
                ("Trigonometric ratios", "Define and evaluate trigonometric ratios for relevant angles."),
            )),
            ("Identities and Multiple Angles", "Trigonometric identities, sum and difference formulae, and multiple and sub-multiple angles.", (
                ("Trigonometric identities", "Use fundamental trigonometric identities to simplify expressions."),
                ("Sum and difference formulae", "Apply trigonometric formulae for sums and differences of angles."),
                ("Multiple and sub-multiple angles", "Apply formulae for multiple and sub-multiple angles."),
            )),
            ("Inverse Trigonometric Functions", "Inverse trigonometric functions and their basic properties.", (
                ("Inverse trigonometric functions", "Interpret inverse trigonometric functions and their principal values."),
            )),
            ("Applications of Trigonometry", "Heights and distances and properties of triangles.", (
                ("Heights and distances", "Solve practical height-and-distance problems using trigonometric ratios."),
                ("Properties of triangles", "Apply trigonometric relationships to triangle problems."),
            )),
        ),
    ),
    (
        "Analytical Geometry of Two and Three Dimensions",
        "Coordinate geometry of lines, circles, conics, points, planes and spheres in two and three dimensions.",
        (
            ("Coordinate Geometry in Two Dimensions", "Rectangular Cartesian coordinates, distance formula and equations of lines.", (
                ("Cartesian coordinates and distance", "Locate points in the rectangular Cartesian coordinate system and calculate distances."),
                ("Equations of a line", "Write equations of a line in various forms."),
                ("Angles between lines", "Find and use the angle between two lines."),
                ("Distance from a point to a line", "Calculate the perpendicular distance from a point to a line."),
            )),
            ("Circles and Conic Sections", "Standard and general equations of a circle, and standard forms and properties of conics.", (
                ("Circle", "Use the standard and general forms of the equation of a circle."),
                ("Parabola", "Recognise standard forms of a parabola and interpret its basic parameters."),
                ("Ellipse", "Recognise standard forms of an ellipse and interpret its basic parameters."),
                ("Hyperbola", "Recognise standard forms of a hyperbola and interpret its basic parameters."),
                ("Eccentricity and axes of a conic", "Interpret the eccentricity and axes of conic sections."),
            )),
            ("Coordinate Geometry in Three Dimensions", "Points and distances in three-dimensional space, direction ratios and cosines, lines, planes and spheres.", (
                ("Points and distance in three dimensions", "Represent points in three-dimensional space and calculate the distance between two points."),
                ("Direction ratios and cosines", "Use direction ratios and direction cosines to describe directions in space."),
                ("Equations of lines and planes", "Write equations of a line and a plane in various forms."),
                ("Angles between lines and planes", "Calculate angles between two lines and between two planes."),
                ("Sphere", "Use the equation of a sphere."),
            )),
        ),
    ),
    (
        "Differential Calculus",
        "Functions, limits, continuity, derivatives and applications of derivatives.",
        (
            ("Functions", "Real-valued functions, domain, range, graphs, composite functions and inverse functions.", (
                ("Domain, range and graphs", "Identify the domain and range of a real-valued function and interpret its graph."),
                ("Composite functions", "Form and evaluate composite functions."),
                ("One-to-one and onto functions", "Determine whether a function is one-to-one or onto."),
                ("Inverse functions", "Find and interpret inverse functions where they exist."),
            )),
            ("Limits and Continuity", "The notion of a limit, standard limits and continuity of functions.", (
                ("Limits and standard limits", "Evaluate limits using standard limits and algebraic methods."),
                ("Continuity", "Determine continuity of functions and use algebraic operations on continuous functions."),
            )),
            ("Derivatives", "Derivative at a point, geometric and physical interpretations, derivative rules and second-order derivatives.", (
                ("Derivative at a point", "Interpret the derivative of a function at a point."),
                ("Geometric and physical meaning", "Relate a derivative to a tangent slope and to rates of change."),
                ("Derivative rules", "Differentiate sums, products, quotients, composite functions and functions of another function."),
                ("Second-order derivatives", "Find and interpret second-order derivatives."),
            )),
            ("Applications of Derivatives", "Increasing and decreasing functions and maxima and minima.", (
                ("Increasing and decreasing functions", "Use derivatives to determine intervals of increase and decrease."),
                ("Maxima and minima", "Apply derivatives to problems involving maxima and minima."),
            )),
        ),
    ),
    (
        "Integral Calculus and Differential Equations",
        "Indefinite and definite integration, areas, and ordinary differential equations.",
        (
            ("Indefinite Integration", "Integration as the inverse of differentiation, substitution, integration by parts and standard integrals.", (
                ("Integration as inverse differentiation", "Relate integration to finding antiderivatives."),
                ("Integration by substitution", "Evaluate integrals using a suitable substitution."),
                ("Integration by parts", "Evaluate integrals using integration by parts."),
                ("Standard integrals", "Use standard integrals involving algebraic, trigonometric, exponential and hyperbolic functions."),
            )),
            ("Definite Integrals and Areas", "Evaluation of definite integrals and areas of plane regions bounded by curves.", (
                ("Definite integrals", "Evaluate definite integrals using standard properties and methods."),
                ("Areas bounded by curves", "Determine areas of plane regions bounded by curves using definite integrals."),
            )),
            ("Differential Equations", "Order and degree, formation, general and particular solutions, and first-order first-degree equations.", (
                ("Order and degree", "Identify the order and degree of a differential equation when defined."),
                ("Formation of differential equations", "Form differential equations from families of relations by examples."),
                ("General and particular solutions", "Distinguish general and particular solutions of differential equations."),
                ("First-order first-degree equations", "Solve first-order, first-degree differential equations of the prescribed types."),
                ("Applications of differential equations", "Apply differential equations to suitable problems."),
            )),
        ),
    ),
    (
        "Vector Algebra",
        "Vectors in two and three dimensions and their applications.",
        (
            ("Vectors and Operations", "Magnitude, direction, unit and null vectors, vector addition and scalar multiplication.", (
                ("Magnitude and direction", "Describe vectors in two and three dimensions by magnitude and direction."),
                ("Unit and null vectors", "Identify unit vectors and the null vector."),
                ("Addition and scalar multiplication", "Add vectors and multiply vectors by scalars."),
            )),
            ("Products of Vectors", "Scalar (dot) and vector (cross) products and applications to work, moments and geometry.", (
                ("Scalar or dot product", "Calculate dot products and use them in geometric problems."),
                ("Vector or cross product", "Calculate cross products and use them in geometric problems."),
                ("Work and moment of a force", "Apply vector products to work done by a force and the moment of a force."),
            )),
        ),
    ),
    (
        "Statistics and Probability",
        "Data presentation, measures of central tendency and dispersion, correlation, regression and probability.",
        (
            ("Statistics and Data Presentation", "Classification and frequency distributions, cumulative frequencies, histograms, pie charts and frequency polygons.", (
                ("Classification and frequency distributions", "Classify data and construct frequency and cumulative frequency distributions."),
                ("Graphs of statistical data", "Represent data using histograms, pie charts and frequency polygons."),
                ("Mean, median and mode", "Calculate and interpret measures of central tendency."),
                ("Variance and standard deviation", "Determine and compare variance and standard deviation."),
                ("Correlation and regression", "Interpret correlation and regression."),
            )),
            ("Probability", "Random experiments, events, probability rules, conditional probability, Bayes' theorem and the binomial distribution.", (
                ("Experiments, outcomes and sample spaces", "Identify random experiments, outcomes and associated sample spaces."),
                ("Types and operations of events", "Work with mutually exclusive, exhaustive, impossible, certain, complementary, elementary and composite events, including unions and intersections."),
                ("Classical and statistical probability", "Define probability using classical and statistical approaches and solve elementary problems."),
                ("Elementary probability theorems", "Apply elementary probability theorems to simple problems."),
                ("Conditional probability and Bayes' theorem", "Solve simple problems involving conditional probability and Bayes' theorem."),
                ("Random variables and binomial distribution", "Interpret a random variable as a function on a sample space and recognise experiments that give rise to a binomial distribution."),
            )),
        ),
    ),
)


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    math_subject_id = connection.execute(
        sa.text("SELECT id FROM subjects WHERE code = 'MATH' ORDER BY display_order LIMIT 1")
    ).scalar_one_or_none()
    if math_subject_id is None:
        return

    for chapter_order, (chapter_name, chapter_description, topics) in enumerate(SYLLABUS, start=1):
        chapter_id = _ensure(
            connection,
            "chapters",
            {"subject_id": math_subject_id, "name": chapter_name},
            {
                "subject_id": math_subject_id,
                "name": chapter_name,
                "description": chapter_description,
                "display_order": chapter_order,
            },
            now,
        )
        for topic_order, (topic_name, topic_description, concepts) in enumerate(topics, start=1):
            if topic_name == "Probability":
                topic_id = _move_existing_probability(
                    connection, math_subject_id, chapter_id, topic_description, topic_order, now
                )
            else:
                topic_id = _ensure(
                    connection,
                    "topics",
                    {"chapter_id": chapter_id, "name": topic_name},
                    {
                        "chapter_id": chapter_id,
                        "name": topic_name,
                        "description": topic_description,
                        "display_order": topic_order,
                    },
                    now,
                )
            for concept_order, (concept_name, concept_description) in enumerate(concepts, start=1):
                _ensure(
                    connection,
                    "concepts",
                    {"topic_id": topic_id, "name": concept_name},
                    {
                        "topic_id": topic_id,
                        "name": concept_name,
                        "description": concept_description,
                        "display_order": concept_order,
                    },
                    now,
                )

    connection.execute(
        sa.text("UPDATE chapters SET display_order = 9 WHERE subject_id = :subject_id AND name = 'Arithmetic'"),
        {"subject_id": math_subject_id},
    )


def _move_existing_probability(
    connection,
    subject_id: object,
    chapter_id: object,
    description: str,
    display_order: int,
    now: datetime,
) -> object:
    existing_id = connection.execute(
        sa.text(
            "SELECT topics.id FROM topics "
            "JOIN chapters ON chapters.id = topics.chapter_id "
            "WHERE chapters.subject_id = :subject_id AND topics.name = 'Probability' "
            "ORDER BY topics.display_order LIMIT 1"
        ),
        {"subject_id": subject_id},
    ).scalar_one_or_none()
    if existing_id is None:
        return _ensure(
            connection,
            "topics",
            {"chapter_id": chapter_id, "name": "Probability"},
            {
                "chapter_id": chapter_id,
                "name": "Probability",
                "description": description,
                "display_order": display_order,
            },
            now,
        )
    connection.execute(
        sa.text(
            "UPDATE topics SET chapter_id = :chapter_id, description = :description, "
            "display_order = :display_order, updated_at = :updated_at WHERE id = :id"
        ),
        {
            "chapter_id": chapter_id,
            "description": description,
            "display_order": display_order,
            "updated_at": now,
            "id": existing_id,
        },
    )
    return existing_id


def _ensure(
    connection,
    table_name: str,
    lookup: dict[str, object],
    values: dict[str, object],
    now: datetime,
) -> object:
    where_clause = " AND ".join(f"{column} = :lookup_{column}" for column in lookup)
    parameters = {f"lookup_{column}": value for column, value in lookup.items()}
    existing_id = connection.execute(
        sa.text(f"SELECT id FROM {table_name} WHERE {where_clause} LIMIT 1"), parameters
    ).scalar_one_or_none()
    if existing_id is not None:
        return existing_id

    record = {
        **values,
        "id": _database_value(
            connection,
            uuid5(NAMESPACE, f"{table_name}:{'|'.join(str(value) for value in lookup.values())}"),
        ),
        "created_at": now,
        "updated_at": now,
    }
    columns = ", ".join(record)
    placeholders = ", ".join(f":{column}" for column in record)
    connection.execute(
        sa.text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"), record
    )
    return record["id"]


def _database_value(connection, value: object) -> object:
    if isinstance(value, UUID) and connection.dialect.name == "sqlite":
        return value.hex
    return str(value) if isinstance(value, UUID) else value


def downgrade() -> None:
    pass
