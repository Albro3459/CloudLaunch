### Running React Site:

Update dependencies:
```sh
cd CloudLaunch; 
npm install
```

Run project on local:
```sh
cd react-frontend; 
npm start
````

Keep tailwind css updated while making changes:
```sh
cd react-frontend; 
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch
```

---

### Publish GitHub page:

* NOTE: This uses the your local build code to publish. It does NOT pull from any remote branch. It compiles your code to the build folder and publishes that. 
    * Pro: Can be ran from any branch
    * Con: Must be run locally and it can be confusing

```sh
cd react-frontend; 
npm run publish # publishes to gh-pages branch
````