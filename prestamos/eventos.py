def registrar_evento(request, accion, **datos):
    if not hasattr(request, "eventos_prestamos"):
        request.eventos_prestamos = []
    request.eventos_prestamos.append({"accion": accion, **datos})
