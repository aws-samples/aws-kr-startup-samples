import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const http = require('http');
const { DynamoDB } = require("@aws-sdk/client-dynamodb");
const { ScanCommand } = require("@aws-sdk/lib-dynamodb");
const { DynamoDBDocument } = require("@aws-sdk/lib-dynamodb");

const client = new DynamoDB({});
const docClient = DynamoDBDocument.from(client);
export const handler = async (event) => {
  //promise to fetch AppConfig data
  const res = await new Promise((resolve, reject) => {
    http.get(
      "http://localhost:2772/applications/AWSomeCribRentals/environments/Beta/configurations/CardFeatureFlag",
      resolve
    );
  });
  //get data from AppConfig
  let configData = await new Promise((resolve, reject) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('error', err => reject(err));
    res.on('end', () => resolve(data));
  });
  //parse that data as JSON
  const parsedConfigData = JSON.parse(configData);
  const DynamoParams = {
    TableName: 'AWSCribsRentalMansions'
  };
  //fetch data from Dynamo DB
  async function listItems() {
    try {
      const data = await docClient.send(new ScanCommand(DynamoParams));
      return data;
    } catch (err) {
      console.log(err);
      return err;
    }
  }
  const data = await listItems();

  //figure out how long the loop will be based on whether or not pagination is enabled
  let runUntilVar = 0;

  if (parsedConfigData.pagination.enabled == true) {
    runUntilVar = parsedConfigData.pagination.number;
  }
  else {
    runUntilVar = data.Items.length;
  }

  //create carousel layout if showcarousel is enabled and static image if not
  if (parsedConfigData.showcarousel.enabled == true) {
    let returnhtml = ``;
    try {
      for (let i = 0; i < runUntilVar; i++) {
        returnhtml += `<div class="col-md-4 mt-4">
    		    <div class="card profile-card-5">
    		        <div class="card-img-block">
                        <div class="slideshow-container">`;
        for (let j = 0; j < data.Items[i].Image.length; j++) {
          returnhtml += `<div class="mySlides` + (i + 1) + `">
                    <img class="card-img-top" style="height: 300px;" src="` + data.Items[i].Image[j].name + `" style="width:100%">
                  </div>`;
        }
        returnhtml += `</div>`;

        if (data.Items[i].Image.length > 1) {
          returnhtml += `<a class="prev" onclick="plusSlides(-1, ` + i + `)">&#10094;</a>
                            <a class="next" onclick="plusSlides(1, ` + i + `)">&#10095;</a>`;
        }

        returnhtml += `</div>
                    <div class="card-body pt-0">
                    <h5 class="card-title">` + data.Items[i].Name + ` <span style="font-size: 0.7em;color:rgb(255, 64, 64)">(` + data.Items[i].Location + `)</span></h5>
                    <p class="card-text">` + data.Items[i].Description + `</p>
                    <a class="btn btn-primary"style="display: inline" href="#">Check Availability</a>
                    <span style="float: right;cursor: pointer;" onclick="favoriteStar(this)"><span class="fa fa-star"></span></span>
                  </div>
                </div>
    		</div>`;
      }
      return {
        statusCode: 200,
        body: returnhtml,
      };
    } catch (err) {
      console.log(err);
      return {
        error: err
      }
    }
  } else {
    let returnhtml = ``;
    try {
      for (let i = 0; i < runUntilVar; i++) {
        returnhtml += `<div class="col-md-4 mt-4">
    		    <div class="card profile-card-5">
    		        <div class="card-img-block">
                    <img class="card-img-top" style="height: 300px;" src="` + data.Items[i].Image[0].name + `" style="width:100%"
                        alt="Card image cap" style="height: 300px;">
    		        </div>
                    <div class="card-body pt-0">
                    <h5 class="card-title">` + data.Items[i].Name + ` <span style="font-size: 0.7em;color:rgb(255, 64, 64)">(` + data.Items[i].Location + `)</span></h5>
                    <p class="card-text">` + data.Items[i].Description + `</p>
                    <a class="btn btn-primary"style="display: inline" href="#">Check Availability</a>
                    <span style="float: right;cursor: pointer;" onclick="favoriteStar(this)"><span class="fa fa-star"></span></span>
                  </div>
                </div>
    		</div>`;
      }
      return {
        statusCode: 200,
        body: returnhtml,
      };
    } catch (err) {
      console.log(err);
      return {
        error: err
      };
    }
  }
};