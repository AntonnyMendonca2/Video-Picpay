from fastapi import Depends, HTTPException, status, FastAPI
from bancoDeDados import conexao
from sqlalchemy.exc import SQLAlchemyError
import os
from twilio.rest import Client
from dotenv import load_dotenv
import requests
import json
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)



load_dotenv()

app = FastAPI()

def enviar_mensagem(numero, mensagem):
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=mensagem,
        from_="+19785060846",
        to=f"+55{numero}",
    )
    return message.body



@app.post("/transacao", response_model=conexao.TrasacaoCreate)
def criar_transacao(transacao: conexao.TrasacaoCreate, db: conexao.Session = Depends(conexao.get_db)):
    logging.info("Retornando usuario de origem")
    id_origem = db.query(conexao.Usuario).filter(conexao.Usuario.cpf_cnpj == transacao.cpf_cnpj_origem).first()
    logging.info("Retornando usuario de destino")
    id_destino = db.query(conexao.Usuario).filter(conexao.Usuario.cpf_cnpj == transacao.cpf_cnpj_destino).first()
    logging.info("Validando se é um lojista")
    if len(id_origem.cpf_cnpj) == 14:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lojistas não podem efetuar transações")
    else:
        logging.info("Validando se tem saldo")
        if id_origem.saldo < transacao.valor:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Saldo insuficiente")
        else:
            logging.info("Validando se há um destinatário no DB")
            if id_destino is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Usuário destino não encontrado {id_destino}")
            else:
                try:
                    logging.info("Diminuindo saldo do usuário de origem")
                    conexao.diminuir_valor(db, transacao.cpf_cnpj_origem, transacao.valor)
                    logging.info("Aumentando saldo do usuário de destino")
                    conexao.aumentar_valor(db, transacao.cpf_cnpj_destino, transacao.valor)
                    logging.info("Criando registro de transação")
                    conexao.criar_transacao(db, cpf_cnpj_origem=transacao.cpf_cnpj_origem, cpf_cnpj_destino=transacao.cpf_cnpj_destino, valor=transacao.valor)
                    # {"status" : "fail", "data" : { "authorization" : false }}
                    logging.info("Chamando autorizador")
                    authorizer = requests.get("https://util.devi.tools/api/v2/authorize")
                    logging.info("Lendo resposta do autorizador")
                    if authorizer.status_code == 200:
                        authorizer = authorizer.json()
                        if authorizer.get("status") == "fail":
                            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transação não autorizada")
                        else:
                            logging.info("subindo para o banco")
                            db.commit()
                            logging.info("enviar notificação")
                            enviar_mensagem(numero=id_origem.telefone, mensagem=f"Transação no valor de R$ {transacao.valor} efetuada com sucesso para o usuário {id_destino.nome}")
                            return {
                                "cpf_cnpj_origem": transacao.cpf_cnpj_origem,
                                "cpf_cnpj_destino": transacao.cpf_cnpj_destino,
                                "valor": transacao.valor
                         } 
                    else:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transação não autorizada") 
                except SQLAlchemyError as e:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao criar transação: {e}")
                finally:
                    db.close()

@app.post("/adicionar-saldo", response_model=conexao.SaldoPush)
def adicionar_saldo(saldo: conexao.SaldoPush, db: conexao.Session = Depends(conexao.get_db)):
    logging.info("Aumentando valor do usuario informado")
    try:
        conexao.aumentar_valor(db=db, cpf_cnpj=saldo.cpf_cnpj_origem, valor=saldo.valor)
        db.commit()
        logging.info("Sucesso!")
        return {
            "cpf_cnpj_origem": saldo.cpf_cnpj_origem,
            "valor": saldo.valor
        }
    except Exception as e:
        logging.info("Algo deu errado")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao adicionar saldo: {e}")
    finally:
        db.close()


# if __name__=="__main__":
#     numero = os.environ["MEU_NUMERO"]
#     enviar_mensagem(numero=numero, mensagem="teste")