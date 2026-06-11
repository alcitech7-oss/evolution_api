FROM node:18-alpine

# Instalar dependências do sistema
RUN apk add --no-cache git

# Instalar a Evolution API globalmente
RUN npm install -g evolution-api

# Criar diretório de trabalho
WORKDIR /evolution

# Expor a porta padrão
EXPOSE 8080

# Comando para iniciar
CMD ["evolutionapi"]
