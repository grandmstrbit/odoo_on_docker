FROM odoo:17

# Установка pip и библиотеки transliterate
USER root
RUN apt-get update
RUN apt-get install -y python3-pip

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

# Указываем рабочую директорию
WORKDIR /var/lib/odoo

# Экспонируем порт Odoo
EXPOSE 8069 8072

# Запускаем Odoo
CMD ["odoo"]
