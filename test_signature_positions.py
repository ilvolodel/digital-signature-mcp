#!/usr/bin/env python3
"""
Script di test per le posizioni del talloncino di firma.

Questo script testa tutte le 7 posizioni predefinite e una posizione custom
calcolando le coordinate per un PDF A4 standard.

Non firma realmente i documenti, ma mostra le coordinate che verrebbero utilizzate.
"""

from typing import Optional, Dict


def get_signature_position(
    position: str = "bottom-right",
    page_width: int = 595,
    page_height: int = 842,
    custom_coords: Optional[Dict[str, int]] = None
) -> Dict[str, int]:
    """
    Calcola le coordinate (llx, lly, urx, ury) per il talloncino di firma.
    (Copia della funzione da app/main.py per testing standalone)
    """
    SIGNATURE_WIDTH = 80
    SIGNATURE_HEIGHT = 30
    MARGIN = 15
    
    if position == "custom" and custom_coords:
        return {
            "llx": custom_coords.get("llx", 500),
            "lly": custom_coords.get("lly", 60),
            "urx": custom_coords.get("urx", 580),
            "ury": custom_coords.get("ury", 90)
        }
    
    positions = {
        "bottom-right": {
            "llx": page_width - SIGNATURE_WIDTH - MARGIN,
            "lly": MARGIN,
            "urx": page_width - MARGIN,
            "ury": MARGIN + SIGNATURE_HEIGHT
        },
        "bottom-left": {
            "llx": MARGIN,
            "lly": MARGIN,
            "urx": MARGIN + SIGNATURE_WIDTH,
            "ury": MARGIN + SIGNATURE_HEIGHT
        },
        "bottom-center": {
            "llx": (page_width - SIGNATURE_WIDTH) // 2,
            "lly": MARGIN,
            "urx": (page_width + SIGNATURE_WIDTH) // 2,
            "ury": MARGIN + SIGNATURE_HEIGHT
        },
        "top-right": {
            "llx": page_width - SIGNATURE_WIDTH - MARGIN,
            "lly": page_height - SIGNATURE_HEIGHT - MARGIN,
            "urx": page_width - MARGIN,
            "ury": page_height - MARGIN
        },
        "top-left": {
            "llx": MARGIN,
            "lly": page_height - SIGNATURE_HEIGHT - MARGIN,
            "urx": MARGIN + SIGNATURE_WIDTH,
            "ury": page_height - MARGIN
        },
        "top-center": {
            "llx": (page_width - SIGNATURE_WIDTH) // 2,
            "lly": page_height - SIGNATURE_HEIGHT - MARGIN,
            "urx": (page_width + SIGNATURE_WIDTH) // 2,
            "ury": page_height - MARGIN
        },
        "center": {
            "llx": (page_width - SIGNATURE_WIDTH) // 2,
            "lly": (page_height - SIGNATURE_HEIGHT) // 2,
            "urx": (page_width + SIGNATURE_WIDTH) // 2,
            "ury": (page_height + SIGNATURE_HEIGHT) // 2
        }
    }
    
    return positions.get(position, positions["bottom-right"])


def print_coordinates(position_name, coords):
    """Stampa le coordinate in formato leggibile"""
    print(f"\n📍 {position_name}")
    print(f"   Lower-Left (llx, lly):  ({coords['llx']:3}, {coords['lly']:3})")
    print(f"   Upper-Right (urx, ury): ({coords['urx']:3}, {coords['ury']:3})")
    print(f"   Dimensioni: {coords['urx'] - coords['llx']}x{coords['ury'] - coords['lly']} punti")


def visualize_position(position_name, coords, page_width=595, page_height=842):
    """Crea una visualizzazione ASCII della posizione del talloncino"""
    print(f"\n🖼️  Visualizzazione: {position_name}")
    print("   ┌" + "─" * 40 + "┐")
    
    # Determina dove posizionare il marcatore
    llx_pct = coords['llx'] / page_width
    lly_pct = coords['lly'] / page_height
    
    # 20 righe di visualizzazione
    for row in range(20, -1, -1):
        row_pct = row / 20
        line = "   │"
        
        # 38 colonne di visualizzazione
        for col in range(38):
            col_pct = col / 38
            
            # Verifica se siamo dentro il rettangolo della firma
            in_width = (coords['llx'] / page_width) <= col_pct <= (coords['urx'] / page_width)
            in_height = (coords['lly'] / page_height) <= row_pct <= (coords['ury'] / page_height)
            
            if in_width and in_height:
                line += "█"
            else:
                line += " "
        
        line += "│"
        print(line)
    
    print("   └" + "─" * 40 + "┘")


def main():
    """Test principale"""
    print("=" * 60)
    print("  TEST POSIZIONAMENTO TALLONCINO DI FIRMA")
    print("=" * 60)
    print("\n📄 Dimensioni pagina A4: 595 x 842 punti")
    print("📏 Dimensioni talloncino: 80 x 30 punti")
    print("📐 Margine dai bordi: 15 punti")
    
    # Test tutte le 7 posizioni predefinite
    positions = [
        "bottom-right",
        "bottom-left",
        "bottom-center",
        "top-right",
        "top-left",
        "top-center",
        "center"
    ]
    
    print("\n" + "=" * 60)
    print("  POSIZIONI PREDEFINITE")
    print("=" * 60)
    
    for pos in positions:
        coords = get_signature_position(position=pos)
        print_coordinates(pos.upper().replace("-", " "), coords)
        visualize_position(pos.upper().replace("-", " "), coords)
    
    # Test posizione custom
    print("\n" + "=" * 60)
    print("  POSIZIONE CUSTOM")
    print("=" * 60)
    
    custom = {"llx": 250, "lly": 400, "urx": 330, "ury": 430}
    coords = get_signature_position(position="custom", custom_coords=custom)
    print_coordinates("CUSTOM (Centro-pagina custom)", coords)
    visualize_position("CUSTOM", coords)
    
    # Riepilogo
    print("\n" + "=" * 60)
    print("  COME USARE NEL TOOL sign_document")
    print("=" * 60)
    
    print("""
Esempio 1 - Posizione predefinita:
    sign_document(
        ...,
        signature_position="bottom-left"
    )

Esempio 2 - Posizione custom:
    sign_document(
        ...,
        signature_position="custom",
        custom_coords={"llx": 250, "lly": 400, "urx": 330, "ury": 430}
    )
    
Esempio 3 - Default (bottom-right):
    sign_document(...)  # Nessun parametro necessario
    """)
    
    print("=" * 60)
    print("✅ Test completato!")
    print("=" * 60)


if __name__ == "__main__":
    main()
