### Running React Site:

Update dependencies:
```sh
cd VPN_CLOUD_AUTOMATION; 
npm install
```

Run project on local:
```sh
cd vpn-frontend; 
npm start
````

Keep tailwind css updated while making changes:
```sh
cd vpn-frontend; 
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch
```

---

### Deploy GitHub page:

Push changes to main or dev, then:
```sh
cd vpn-frontend; 
npm run deploy # Deploys to gh-pages branch
````