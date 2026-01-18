from mss import mss

with mss() as sct:
    print("Mapeamento de Monitores Detectados:")
    for i, monitor in enumerate(sct.monitors):
        if i == 0: continue # O índice 0 é "Todos os monitores juntos", ignore.
        print(f"Monitor {i}: Resolução {monitor['width']}x{monitor['height']} (Posição: Left={monitor['left']}, Top={monitor['top']})")