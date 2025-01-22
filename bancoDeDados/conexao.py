from sqlalchemy.orm import Session, relationship, sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, TIMESTAMP, DECIMAL, func
from decimal import Decimal
from pydantic import BaseModel

url_banco = "mysql+pymysql://root:root@localhost:3306/Banco"

try:
    engine = create_engine(url_banco)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except SQLAlchemyError as e:
    print("Erro ao conectar com o banco de dados: ", e)

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuario"
    
    id = Column(Integer, primary_key=True, autoincrement=True)                    # id int AUTO_INCREMENT primary key,
    nome = Column(String(200), nullable=False)                        # nome varchar(200) not null,
    cpf_cnpj = Column(String(14), nullable=False, unique=True)                    # cpf_cnpj varchar(14) not null unique,
    email = Column(String(200), nullable=False, unique=True)                    # email varchar(100) not null unique,
    saldo = Column(DECIMAL(10,2), default=0.00)                    # saldo decimal(10, 2) default 0.00,
    telefone = Column(String(11), nullable=False)                        # telefone varchar(11) not null,
    criado_em = Column(TIMESTAMP, default="CURRENT_TIMESTAMP")      # criado_em TIMESTAMP default CURRENT_TIMESTAMP,        

class Transacao(Base):
    __tablename__ = "transacao"

    id = Column(Integer, primary_key=True, autoincrement=True)                   # id int auto_increment primary key,
    id_origem = Column(Integer, ForeignKey("usuario.id"), nullable=False)                    # id_origem int not null,
    id_destino = Column(Integer, ForeignKey("usuario.id"), nullable=False)                    # id_destino int not null,
    valor = Column(DECIMAL(10, 2), nullable=False)                    # valor decimal(10,2) not null,
    criado_em = Column(TIMESTAMP, server_default=func.current_timestamp())                   # criado_em TIMESTAMP default CURRENT_TIMESTAMP,
    origem = relationship("Usuario", foreign_keys=[id_origem])                    # foreign key (id_origem) references usuario(id),
    destino = relationship("Usuario", foreign_keys=[id_destino])                    # foreign key (id_destino) references usuario(id)

class TrasacaoCreate(BaseModel):
    cpf_cnpj_origem: str
    cpf_cnpj_destino: str
    valor: float

class SaldoPush(BaseModel):
    cpf_cnpj_origem: str
    valor: float

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def diminuir_valor(db: Session, cpf_cnpj: str, valor: float):
    valor = Decimal(valor)
    usuario = db.query(Usuario).filter(Usuario.cpf_cnpj == cpf_cnpj).first()
    usuario.saldo -= valor
    db.flush()
    return usuario.saldo

def aumentar_valor(db: Session, cpf_cnpj: str, valor: float):
    valor = Decimal(valor)
    usuario = db.query(Usuario).filter(Usuario.cpf_cnpj == cpf_cnpj).first()
    usuario.saldo += valor
    db.flush()
    return usuario.saldo

def criar_transacao(db: Session, cpf_cnpj_origem: int, cpf_cnpj_destino: int, valor: float):
    valor = Decimal(valor)
    id_origem = db.query(Usuario).filter(Usuario.cpf_cnpj == cpf_cnpj_origem).first()
    id_destino = db.query(Usuario).filter(Usuario.cpf_cnpj == cpf_cnpj_destino).first()
    transacao = Transacao(
        id_origem=id_origem.id,
        id_destino=id_destino.id,
        valor=valor
    )
    db.add(transacao)
    db.flush()
    return transacao

if __name__=="__main__":
    db = SessionLocal()
    criar_transacao(db=db, cpf_cnpj_origem="87978556330", cpf_cnpj_destino="87978556324", valor=35.00)
