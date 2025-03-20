### Running React Site:

Update dependencies:
```
cd VPN_CLOUD_AUTOMATION; 
npm install
```

Run project on local:
```
cd vpn-frontend; 
npm start
````

Keep tailwind css updated while making changes:
```
cd vpn-frontend; 
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch
```

### Deploy GitHub page:

Push changes to main or dev

Then:
```
cd vpn-frontend; 
npm run deploy # Deploys to gh-pages branch
````