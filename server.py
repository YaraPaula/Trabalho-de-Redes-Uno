import socket
import ssl
import threading
from room import Room
import time


HOST = "0.0.0.0"
PORT = 5000

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

rooms = {}
room_id_counter = 1
rooms_lock = threading.Lock()


def handle_client(conn, addr):
    print(f"[CONEXÃO] {addr} conectado")

    conn.sendall(
        b"Bem-vindo ao UNO!\n"
        b"Use: nick <nome>\n"
        b"Depois: create | join <id>\n"
    )

    buffer = ""

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            buffer += data.decode()

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if not line:
                    continue

                print(f"[{addr}] {line}")
                parts = line.split()
                cmd = parts[0].lower()

                if not hasattr(conn, "nickname") and cmd != "nick":
                    conn.sendall(b"ERROR;SET_NICK_FIRST\n")
                    continue

                if cmd == "nick" and len(parts) == 2:
                    conn.nickname = parts[1]
                    conn.sendall(f"NICK_OK;{conn.nickname}\n".encode())

                elif cmd == "create":
                    create_room(conn)

                elif cmd == "list":
                    with rooms_lock:
                        if not rooms:
                            conn.sendall(b"NO_ROOMS\n")
                        else:
                            for rid, room in rooms.items():
                                conn.sendall(
                                    f"ROOM;{rid};{len(room.players)}\n".encode()
                                )

                elif cmd == "join" and len(parts) == 2:
                    if not parts[1].isdigit():
                        conn.sendall(b"ERROR;INVALID_ROOM_ID\n")
                        continue
                    join_room(conn, int(parts[1]))

                elif cmd in ("ok", "hand", "draw", "play", "wild", "uno"):
                    if hasattr(conn, "room"):
                        conn.room.handle(conn, line)
                    else:
                        conn.sendall(b"ERROR;NOT_IN_ROOM\n")

                elif cmd in ("quit", "exit"):
                    return

                else:
                    conn.sendall(b"ERROR;UNKNOWN_COMMAND\n")

    except Exception as e:
        print("[ERRO CLIENTE]", e)

    finally:
        if hasattr(conn, "room"):
            conn.room.remove_player(conn)
        conn.close()
        print(f"[DESCONECTADO] {addr}")


def create_room(conn):
    global room_id_counter

    with rooms_lock:
        room = Room(room_id_counter)
        rooms[room_id_counter] = room
        rid = room_id_counter
        room_id_counter += 1

    room.add_player(conn)
    conn.room = room
    room.start()

    conn.sendall(f"ROOM_CREATED;{rid}\n".encode())
    print(f"[SALA] Sala {rid} criada")


def join_room(conn, rid):
    with rooms_lock:
        room = rooms.get(rid)

    if not room:
        conn.sendall(b"ERROR;ROOM_NOT_FOUND\n")
        return

    room.add_player(conn)
    conn.room = room
    conn.sendall(f"ROOM_JOINED;{rid}\n".encode())
    print(f"[SALA] Jogador entrou na sala {rid}")

def cleanup_rooms():
    while True:
        with rooms_lock:
            to_delete = [
                rid for rid, room in rooms.items()
                if not room.running and not room.players
            ]
            for rid in to_delete:
                del rooms[rid]
                print(f"[SALA] Sala {rid} removida")
        time.sleep(10)



def start_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen()

    print(f"[SERVIDOR] Rodando em {HOST}:{PORT} (TLS)")

    threading.Thread(
        target=cleanup_rooms,
        daemon=True
        ).start()


    while True:
        raw_conn, addr = sock.accept()
        try:
            conn = context.wrap_socket(raw_conn, server_side=True)
        except ssl.SSLError as e:
            print("[TLS ERROR]", e)
            raw_conn.close()
            continue

        threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    start_server()
