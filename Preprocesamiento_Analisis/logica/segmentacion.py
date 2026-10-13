def segmentar_senal(datos, tam_ventana):

    ventanas = []

    for inicio in range(0, len(datos), tam_ventana):

        fin = inicio + tam_ventana

        if fin <= len(datos):

            ventanas.append(datos[inicio:fin])

    return ventanas 

