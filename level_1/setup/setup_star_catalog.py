"""
Level 1: Star Catalog Setup

This script creates and populates the BigQuery star_catalog table
that will be used for astronomical triangulation.

Run this after setup_env.sh to create the star catalog.
"""

import os
import sys
from google.cloud import bigquery

# =============================================================================
# CONFIGURATION - Use environment variable (set by setup_env.sh)
# =============================================================================

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")

if not PROJECT_ID:
    print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
    print("   Run: source ~/way-back-home/set_env.sh")
    print("   Or:  export GOOGLE_CLOUD_PROJECT=your-project-id")
    sys.exit(1)

DATASET_ID = "way_back_home"
TABLE_ID = "star_catalog"

# Star catalog data mapping stellar features to biomes/quadrants
STAR_CATALOG_DATA = [
    # CRYO biome (Northwest quadrant)
    {"primary_star": "blue_giant", "nebula_type": "ice_blue", "stellar_color": "blue_white", "quadrant": "NW", "biome": "CRYO"},
    {"primary_star": "blue_giant", "nebula_type": "crystalline", "stellar_color": "blue_white", "quadrant": "NW", "biome": "CRYO"},
    {"primary_star": "blue_supergiant", "nebula_type": "ice_blue", "stellar_color": "cyan", "quadrant": "NW", "biome": "CRYO"},

    # VOLCANIC biome (Northeast quadrant)
    {"primary_star": "red_dwarf", "nebula_type": "orange_red", "stellar_color": "red_orange", "quadrant": "NE", "biome": "VOLCANIC"},
    {"primary_star": "red_dwarf_binary", "nebula_type": "fire", "stellar_color": "red_orange", "quadrant": "NE", "biome": "VOLCANIC"},
    {"primary_star": "red_giant", "nebula_type": "orange_red", "stellar_color": "deep_red", "quadrant": "NE", "biome": "VOLCANIC"},

    # BIOLUMINESCENT biome (Southwest quadrant)
    {"primary_star": "green_pulsar", "nebula_type": "purple_magenta", "stellar_color": "green_purple", "quadrant": "SW", "biome": "BIOLUMINESCENT"},
    {"primary_star": "pulsar", "nebula_type": "purple", "stellar_color": "green", "quadrant": "SW", "biome": "BIOLUMINESCENT"},
    {"primary_star": "magnetar", "nebula_type": "bioluminescent", "stellar_color": "cyan_purple", "quadrant": "SW", "biome": "BIOLUMINESCENT"},

    # FOSSILIZED biome (Southeast quadrant)
    {"primary_star": "yellow_sun", "nebula_type": "golden", "stellar_color": "yellow_gold", "quadrant": "SE", "biome": "FOSSILIZED"},
    {"primary_star": "yellow_dwarf", "nebula_type": "amber", "stellar_color": "warm_yellow", "quadrant": "SE", "biome": "FOSSILIZED"},
    {"primary_star": "orange_sun", "nebula_type": "golden_brown", "stellar_color": "amber", "quadrant": "SE", "biome": "FOSSILIZED"},
]


def create_dataset(client: bigquery.Client):
    """Create the dataset if it doesn't exist."""
    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

    try:
        client.get_dataset(dataset_ref)
        print(f"✓ Dataset {DATASET_ID} already exists")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        dataset.description = "Way Back Home workshop data"
        client.create_dataset(dataset)
        print(f"✓ Created dataset {DATASET_ID}")


def create_star_catalog_table(client: bigquery.Client):
    """Create and populate the star_catalog table."""
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    # Define schema
    schema = [
        bigquery.SchemaField("primary_star", "STRING", mode="REQUIRED",
                            description="Primary star type (e.g., blue_giant, red_dwarf, green_pulsar, yellow_sun)"),
        bigquery.SchemaField("nebula_type", "STRING", mode="REQUIRED",
                            description="Dominant nebula type in the region"),
        bigquery.SchemaField("stellar_color", "STRING", mode="REQUIRED",
                            description="Overall stellar color temperature"),
        bigquery.SchemaField("quadrant", "STRING", mode="REQUIRED",
                            description="Planet quadrant (NW, NE, SW, SE)"),
        bigquery.SchemaField("biome", "STRING", mode="REQUIRED",
                            description="Biome type (CRYO, VOLCANIC, BIOLUMINESCENT, FOSSILIZED)"),
    ]

    # Create table
    table = bigquery.Table(table_ref, schema=schema)
    table.description = "Star catalog for astronomical triangulation - maps stellar features to planet quadrants"

    try:
        client.delete_table(table_ref)
        print(f"  Deleted existing table {TABLE_ID}")
    except Exception:
        pass

    table = client.create_table(table)
    print(f"✓ Created table {TABLE_ID}")

    # Insert data
    errors = client.insert_rows_json(table_ref, STAR_CATALOG_DATA)

    if errors:
        print(f"✗ Errors inserting data: {errors}")
    else:
        print(f"✓ Inserted {len(STAR_CATALOG_DATA)} rows into {TABLE_ID}")


def verify_setup(client: bigquery.Client):
    """Verify the table is queryable."""
    query = f"""
    SELECT biome, quadrant, COUNT(*) as entries
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    GROUP BY biome, quadrant
    ORDER BY quadrant
    """

    print("\n📊 Star Catalog Summary:")
    print("-" * 40)

    results = client.query(query).result()
    for row in results:
        print(f"  {row.quadrant} ({row.biome}): {row.entries} stellar patterns")

    print("-" * 40)
    print("✓ Star catalog is ready for triangulation queries")


def main():
    """Set up the star catalog for the workshop."""
    print(f"Setting up star catalog in project: {PROJECT_ID}")
    print("=" * 50)

    client = bigquery.Client(project=PROJECT_ID)

    create_dataset(client)
    create_star_catalog_table(client)
    verify_setup(client)

    print("\n" + "=" * 50)
    print("✅ Star catalog setup complete!")
    print(f"   Table: {PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")


if __name__ == "__main__":
    main()
