"""Frozen dataclasses for PBIR (Power BI Enhanced Report Format) structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# -- PBIR Schema URLs -------------------------------------------------------

SCHEMA_REPORT = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/report/1.2.0/schema.json"
)
SCHEMA_PAGE = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/page/2.1.0/schema.json"
)
SCHEMA_PAGES_METADATA = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
)
SCHEMA_VERSION = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/versionMetadata/1.0.0/schema.json"
)
SCHEMA_VISUAL_CONTAINER = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/visualContainer/2.7.0/schema.json"
)
SCHEMA_BOOKMARKS_METADATA = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json"
)
SCHEMA_BOOKMARK = (
    "https://developer.microsoft.com/json-schemas/"
    "fabric/item/report/definition/bookmark/2.1.0/schema.json"
)


# -- Visual type identifiers ------------------------------------------------

SUPPORTED_VISUAL_TYPES: frozenset[str] = frozenset(
    {
        # Original 9
        "barChart",
        "lineChart",
        "card",
        "pivotTable",
        "tableEx",
        "slicer",
        "kpi",
        "gauge",
        "donutChart",
        # v3.1.0 additions
        "columnChart",
        "areaChart",
        "ribbonChart",
        "waterfallChart",
        "scatterChart",
        "funnelChart",
        "multiRowCard",
        "treemap",
        "cardNew",
        "stackedBarChart",
        "lineStackedColumnComboChart",
        # v3.4.0 additions
        "cardVisual",
        "actionButton",
        # v3.5.0 additions (confirmed from HR Analysis Desktop export)
        "clusteredColumnChart",
        "clusteredBarChart",
        "textSlicer",
        "listSlicer",
        # v3.6.0 additions (confirmed from HR Analysis Desktop export)
        "image",
        "shape",
        "textbox",
        "pageNavigator",
        "advancedSlicerVisual",
        # v3.8.0 additions
        "azureMap",
    }
)

# Mapping from user-friendly names to PBIR visualType identifiers
VISUAL_TYPE_ALIASES: dict[str, str] = {
    # Original 9
    "bar_chart": "barChart",
    "bar": "barChart",
    "line_chart": "lineChart",
    "line": "lineChart",
    "card": "card",
    "table": "tableEx",
    "matrix": "pivotTable",
    "slicer": "slicer",
    "kpi": "kpi",
    "gauge": "gauge",
    "donut": "donutChart",
    "donut_chart": "donutChart",
    "pie": "donutChart",
    # v3.1.0 additions
    "column": "columnChart",
    "column_chart": "columnChart",
    "area": "areaChart",
    "area_chart": "areaChart",
    "ribbon": "ribbonChart",
    "ribbon_chart": "ribbonChart",
    "waterfall": "waterfallChart",
    "waterfall_chart": "waterfallChart",
    "scatter": "scatterChart",
    "scatter_chart": "scatterChart",
    "funnel": "funnelChart",
    "funnel_chart": "funnelChart",
    "multi_row_card": "multiRowCard",
    "treemap": "treemap",
    "card_new": "cardNew",
    "new_card": "cardNew",
    "stacked_bar": "stackedBarChart",
    "stacked_bar_chart": "stackedBarChart",
    "combo": "lineStackedColumnComboChart",
    "combo_chart": "lineStackedColumnComboChart",
    # v3.4.0 additions
    "card_visual": "cardVisual",
    "modern_card": "cardVisual",
    "action_button": "actionButton",
    "button": "actionButton",
    # v3.5.0 additions
    "clustered_column": "clusteredColumnChart",
    "clustered_column_chart": "clusteredColumnChart",
    "clustered_bar": "clusteredBarChart",
    "clustered_bar_chart": "clusteredBarChart",
    "text_slicer": "textSlicer",
    "list_slicer": "listSlicer",
    # v3.6.0 additions
    "img": "image",
    "text_box": "textbox",
    "page_navigator": "pageNavigator",
    "page_nav": "pageNavigator",
    "navigator": "pageNavigator",
    "advanced_slicer": "advancedSlicerVisual",
    "adv_slicer": "advancedSlicerVisual",
    "tile_slicer": "advancedSlicerVisual",
    # v3.8.0 additions
    "azure_map": "azureMap",
    "map": "azureMap",
}


# -- Default theme -----------------------------------------------------------

DEFAULT_BASE_THEME = {
    "name": "CY24SU06",
    "reportVersionAtImport": "5.55",
    "type": "SharedResources",
}


# -- Dataclasses -------------------------------------------------------------


@dataclass(frozen=True)
class PbirPosition:
    """Visual position and dimensions on a page canvas."""

    x: float
    y: float
    width: float
    height: float
    z: int = 0
    tab_order: int = 0


@dataclass(frozen=True)
class PbirVisual:
    """Summary of a single PBIR visual."""

    name: str
    visual_type: str
    position: PbirPosition
    page_name: str
    folder_path: Path
    has_query: bool = False


@dataclass(frozen=True)
class PbirPage:
    """Summary of a single PBIR page."""

    name: str
    display_name: str
    ordinal: int
    width: int
    height: int
    display_option: str
    visual_count: int
    folder_path: Path


@dataclass(frozen=True)
class PbirReport:
    """Summary of a PBIR report."""

    name: str
    definition_path: Path
    page_count: int
    theme_name: str
    pages: list[PbirPage] = field(default_factory=list)


@dataclass(frozen=True)
class FieldBinding:
    """A single field binding for a visual data role."""

    role: str
    table: str
    column: str
    is_measure: bool = False

    @property
    def qualified_name(self) -> str:
        """Return Table[Column] notation."""
        return f"{self.table}[{self.column}]"
