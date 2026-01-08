import socket
import ssl
import threading
import sys

HOST = "0.tcp.sa.ngrok.io"
PORT = 18525

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw_sock.connect((HOST, PORT))
sock = context.wrap_socket(raw_sock, server_hostname=HOST)

running = True
lock = threading.Lock()

def pretty(line):
    parts = line.split(";")

    if parts[0] == "PLAYER":
        nick = parts[1]
        action = parts[2]

        if action == "JOINED":
            print(f"{nick} entrou na sala")
        elif action == "LEFT":
            print(f"{nick} saiu da sala")
        elif action == "READY":
            print(f"{nick} está pronto")
        elif action == "PLAYED":
            print(f"{nick} jogou {parts[3]} {parts[4]}")
        elif action == "DRAW":
            print(f"{nick} comprou uma carta")
        elif action == "WILD":
            print(f"{nick} jogou WILD → {parts[4]}")
        elif action == "UNO":
            print(f"{nick} gritou UNO!")
        elif action == "UNO_WARNING":
            print(f"{nick} está com UMA carta! (digite UNO)")
        elif action == "WIN":
            print(f"{nick} venceu o jogo!")

    elif parts[0] == "TOP_CARD":
        print(f"\nCarta da mesa: {parts[1]} {parts[2]}\n")

    elif parts[0] == "HAND":
        print("\nSuas cartas:")
        if len(parts) > 1 and parts[1]:
            for c in parts[1].split(","):
                print("  -", c.replace("-", " "))
        else:
            print("  (nenhuma)")
        print()

    elif parts[0] == "GAME_STARTED":
        print("\nO jogo começou!\n")

    elif parts[0] == "YOUR_TURN":
        print("\nÉ A SUA VEZ!\n")

    elif parts[0] == "GAME_OVER":
        print("\n[SERVER] GAME OVER")
        shutdown()

    elif parts[0] == "ERROR":
        print("Erro:", ";".join(parts[1:]))

    else:
        print("[SERVER]", line)


def shutdown():
    global running
    with lock:
        if not running:
            return
        running = False
        try:
            sock.close()
        except:
            pass
    print("Desconectado")
    sys.exit(0)


def listen():
    global running
    try:
        while running:
            data = sock.recv(4096)
            if not data:
                break

            for line in data.decode().splitlines():
                pretty(line)

    except:
        pass
    finally:
        shutdown()


threading.Thread(target=listen, daemon=True).start()

try:
    while running:
        msg = input("> ").strip()
        if not running:
            break
        if msg.lower() in ("quit", "exit"):
            shutdown()
        sock.sendall((msg + "\n").encode())
except:
    shutdown()
