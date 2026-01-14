1. C:\cloudflared\cloudflared.exe tunnel --url http://localhost:8000 --protocol http2 
 

3. https://api.telegram.org/bot8513633381:AAFNswFQQi5z8AQIPfhUOe4Ee-rRWUyGoW8/setWebhook?url=<FROM_THE_BOX>/telegram/webhook ----- to put in web url

4. need to see - {"ok":true,"result":true,"description":"Webhook was set"}

5. https://api.telegram.org/bot8513633381:AAFNswFQQi5z8AQIPfhUOe4Ee-rRWUyGoW8/getWebhookInfo -- to ensure telegram sees webhook

6. in terminal - docker-compose logs -f core-api
to see logs of server 

7. write hi to bot and see the server response 

