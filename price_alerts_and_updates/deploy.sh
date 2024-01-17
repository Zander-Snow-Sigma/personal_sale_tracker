aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin 129033205317.dkr.ecr.eu-west-2.amazonaws.com
docker build --platform "linux/amd64" -t c9-sale-tracker-price-updates .
docker tag c9-sale-tracker-price-updates:latest 129033205317.dkr.ecr.eu-west-2.amazonaws.com/c9-sale-tracker-price-updates:latest
docker push 129033205317.dkr.ecr.eu-west-2.amazonaws.com/c9-sale-tracker-price-updates:latest